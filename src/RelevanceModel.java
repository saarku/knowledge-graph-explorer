import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;

import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.index.Terms;
import org.apache.lucene.index.TermsEnum;
import org.apache.lucene.util.BytesRef;

import io.anserini.rerank.lib.Rm3Reranker;
import io.anserini.rerank.ScoredDocuments;
import io.anserini.util.FeatureVector;
import io.anserini.index.IndexArgs;

public class RelevanceModel {

	private IndexSearcher searcher;
	private QueryCreator creator;
	private IndexReader reader;
	private String fieldName;
	
	public RelevanceModel(IndexSearcher s, QueryCreator c, IndexReader r, String field) throws IOException
	{
		searcher = s;
		creator = c;
		reader = r;
		fieldName = field;
	}
			
	public HashMap<String, Double> getRmVec(String query, int numDocs, int numTerms, HashMap<String, Double> fields) throws IOException {
		HashMap<String, Double> output = new HashMap<>();
		Query q = creator.buildExpandedQuery(new ArrayList<>(), new ArrayList<>(), query, fields, 1.0, true, true);
		TopDocs docs = searcher.search(q, 1000);
		ScoredDocuments sd = ScoredDocuments.fromTopDocs(docs, searcher);
		FeatureVector fv = estimateRelevanceModel(sd, reader, numDocs, numTerms, fieldName, false);	
		
		Double normalizer = 0.0;
		for(String featureName : fv.getFeatures()) {
			output.put(featureName, (double) fv.getFeatureWeight(featureName));
			normalizer += fv.getFeatureWeight(featureName);
		}
		
		for(String t : output.keySet()) {
			output.put(t, output.get(t)/normalizer);
		}
		
		return output;
	}
	
	public HashMap<String, Double> getRmVecIterative(Query initialQuery, int numDocs, int numTerms) throws IOException {
		HashMap<String, Double> output = new HashMap<>();
		
		TopDocs docs = searcher.search(initialQuery, 1000);
		
		ScoredDocuments sd = ScoredDocuments.fromTopDocs(docs, searcher);
		FeatureVector fv = estimateRelevanceModel(sd, reader, numDocs, numTerms, fieldName, false);	
		
		Double normalizer = 0.0;
		for(String featureName : fv.getFeatures()) {
			output.put(featureName, (double) fv.getFeatureWeight(featureName));
			normalizer += fv.getFeatureWeight(featureName);
		}
		
		for(String t : output.keySet()) {
			output.put(t, output.get(t)/normalizer);
		}
		
		return output;
	}
	
	private FeatureVector estimateRelevanceModel(ScoredDocuments docs, IndexReader reader, int fbDocs, int fbTerms, String field, boolean tweetsearch) {
	    FeatureVector f = new FeatureVector();

	    Set<String> vocab = new HashSet<>();
	    int numdocs = docs.documents.length < fbDocs ? docs.documents.length : fbDocs;
	    FeatureVector[] docvectors = new FeatureVector[numdocs];

	    for (int i = 0; i < numdocs; i++) {
	      try {
	        FeatureVector docVector = createdFeatureVector(reader.getTermVector(docs.ids[i], field), reader, tweetsearch);
	        docVector.pruneToSize(fbTerms);

	        vocab.addAll(docVector.getFeatures());
	        docvectors[i] = docVector;
	      } catch (IOException e) {
	        e.printStackTrace();
	        // Just return empty feature vector.
        return f;
      }
    }

    // Precompute the norms once and cache results.
    float[] norms = new float[docvectors.length];
    for (int i = 0; i < docvectors.length; i++) {
      norms[i] = (float) docvectors[i].computeL1Norm();
    }

    for (String term : vocab) {
      float fbWeight = 0.0f;
      for (int i = 0; i < docvectors.length; i++) {
        // Avoids zero-length feedback documents, which causes division by zero when computing term weights.
        // Zero-length feedback documents occur (e.g., with CAR17) when a document has only terms 
        // that accents (which are indexed, but not selected for feedback).
        if (norms[i] > 0.001f) {
          fbWeight += (docvectors[i].getFeatureWeight(term) / norms[i]) * docs.scores[i];
        }
      }
      f.addFeatureWeight(term, fbWeight);
    }

    f.pruneToSize(fbTerms);
    f.scaleToUnitL1Norm();

    return f;
  }
	
	private FeatureVector createdFeatureVector(Terms terms, IndexReader reader, boolean tweetsearch) {
	    FeatureVector f = new FeatureVector();

	    try {
	      int numDocs = reader.numDocs();
	      TermsEnum termsEnum = terms.iterator();

	      BytesRef text;
	      while ((text = termsEnum.next()) != null) {
	        String term = text.utf8ToString();

	        if (term.length() < 2 || term.length() > 20) continue;
	        if (!term.matches("[a-z0-9]+")) continue;

	        int df = reader.docFreq(new Term(fieldName, term));
	        float ratio = (float) df / numDocs;
	        if (tweetsearch) {
	          if (numDocs > 100000000) { // Probably Tweets2013
	            if (ratio > 0.007f) continue;
	          } else {
	            if (ratio > 0.01f) continue;
	          }
	        } else if (ratio > 0.1f) continue;

	        int freq = (int) termsEnum.totalTermFreq();
	        f.addFeatureWeight(term, (float) freq);
	      }
	    } catch (Exception e) {
	      e.printStackTrace();
	      return f;
	    }

	    return f;
    }
}