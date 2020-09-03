import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

import org.apache.lucene.index.Term;
import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.BoostQuery;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.search.BooleanClause.Occur;

public class QueryCreator {
	
	private IndexUtils utils;
	
	public QueryCreator(String indexDir, String stopwordDir) throws IOException {
		utils = new IndexUtils(indexDir, stopwordDir);
	}
	
	public QueryCreator(IndexUtils inputUtils) throws IOException {
		utils = inputUtils;
	}
	
	public HashMap<String, Double> getOrigQueryLM(String query) throws IOException {
		HashMap<String, Double> lmMap = new HashMap<>();
		String analyzedQuery = utils.analyzeText(query);
		String[] terms = analyzedQuery.split(" ");
		
		Double normalizer = 0.0;
		for(String t : terms) {
			lmMap.put(t, lmMap.getOrDefault(t, 0.0) + 1.0);
			normalizer += 1.0;
		}
		
		for(String t : lmMap.keySet()) {
			lmMap.put(t, lmMap.get(t)/normalizer);
		}
		return lmMap;
	}
	
	public HashMap<String, Double> processOriginalQuery(String query, double queryWeight, boolean processFlag) throws IOException {
		HashMap<String, Double> output = new HashMap<>();
		
		String analyzedQuery = query;
		if(processFlag) {
			analyzedQuery = utils.analyzeText(query);
		}
		
		String[] terms = analyzedQuery.split(" ");
		double weight = (1f / (float) terms.length) * queryWeight;
		for(String t : terms) {
			output.put(t, weight);
		}
		return output;
	}
	
	public HashMap<String, Double> processExpansionTerms(ArrayList<String> terms, ArrayList<Double> weights, 
			double expansionWeight, boolean processFlag) throws IOException {
		
		HashMap<String, Double> output = new HashMap<>();
		ArrayList<String> stemmedTerms = new ArrayList<>();
		ArrayList<Double> stemmedWeights = new ArrayList<>();
		
		for(int i = 0; i < terms.size(); i++) {
			String stemmedTerm = terms.get(i);
			if(processFlag) {
				stemmedTerm = utils.analyzeText(terms.get(i));
			}
			if(stemmedTerm.equals("")) continue;
			stemmedTerms.add(stemmedTerm);
			stemmedWeights.add(weights.get(i));
		}
		
		float normalizer = 0f;
		for(Double w : stemmedWeights) {
			normalizer += w;
		}
		
		for(int i = 0; i < stemmedTerms.size(); i++) {
			double finalWeight = (stemmedWeights.get(i) / normalizer) * expansionWeight;
			output.put(stemmedTerms.get(i), finalWeight);
		}
		
		return output;
	}
	
	public Query buildExpandedQuery(ArrayList<String> expansionTerms, ArrayList<Double> expansionWeights, 
			String queryText, HashMap<String,Double> fields, double originalWeight, boolean processOrig, boolean processExp) throws IOException
	{		
		HashMap<String, Double> originalTerms = processOriginalQuery(queryText, originalWeight, processOrig);
		HashMap<String, Double> expansionMap = processExpansionTerms(expansionTerms, expansionWeights, 1-originalWeight, processExp);
		
		// Build the original query
		BooleanQuery originalQuery = null;
		BooleanQuery.Builder originalBooleanQueryBuilder = new BooleanQuery.Builder();
		for(String term : originalTerms.keySet())
		{	
			for(Map.Entry<String, Double> e : fields.entrySet()) {
				Term t = new Term(e.getKey(), term);
				BoostQuery boostQuery = new BoostQuery(new TermQuery(t), (float) (originalTerms.get(term).floatValue() * e.getValue()));
				BooleanClause booleanClause = new BooleanClause(boostQuery, Occur.SHOULD);
				originalBooleanQueryBuilder.add(booleanClause);
			}
		}
		originalQuery = originalBooleanQueryBuilder.build();
		
		if(originalWeight >= 1) {
			return originalQuery;
		}
		
		// Build the expansion part
		BooleanQuery.Builder expansionBooleanQueryBuilder = new BooleanQuery.Builder();
		for(String expansionTerm : expansionMap.keySet())
		{
			for(Map.Entry<String, Double> e : fields.entrySet()) {
				Term t = new Term(e.getKey(), expansionTerm);
				BoostQuery boostQuery = new BoostQuery(new TermQuery(t), (float) (expansionMap.get(expansionTerm).floatValue() * e.getValue()));
				BooleanClause booleanClause = new BooleanClause(boostQuery, Occur.SHOULD);
				expansionBooleanQueryBuilder.add(booleanClause);
			}
		}
		
		if(originalWeight > 0) {
			expansionBooleanQueryBuilder.add(originalQuery, Occur.SHOULD);
		}
		
		return expansionBooleanQueryBuilder.build();
	}
	
	public static Query buildIdQuery(String id, String idField)
	{
		BooleanQuery.Builder termQueryBuilder = new BooleanQuery.Builder();		
		Term t = new Term(idField, id);
		BoostQuery boostQuery = new BoostQuery(new TermQuery(t), 1f);
		BooleanClause booleanClause;
		booleanClause = new BooleanClause(boostQuery, Occur.SHOULD);
		termQueryBuilder.add(booleanClause);
		return termQueryBuilder.build();
	}
	
	public static void main(String[] args) throws IOException {

  		String indexDir = "/Users/saarkuzi/Documents/java_workspace/anserini/lucene-index.robust04.krovetz.pos+docvectors+rawdocs";
  		String stopwordDir = "/Users/saarkuzi/Documents/java_workspace/fig-search/lemur-stopwords.txt";
		QueryCreator creator = new QueryCreator(indexDir, stopwordDir);
		
		ArrayList<String> expansionTerms = new ArrayList<>();
		expansionTerms.add("internal");
		expansionTerms.add("agency");
		expansionTerms.add("enforce");
		
		ArrayList<Double> expansionWeights = new ArrayList<>();
		expansionWeights.add(1.0);
		expansionWeights.add(2.0);
		expansionWeights.add(3.0);
		
		String queryText = "international organized crime"; 
		String fieldName = "contents"; 
		float originalWeight = 0.1f;
	}
}
