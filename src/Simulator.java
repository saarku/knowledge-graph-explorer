import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;

import org.apache.lucene.document.Document;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.BoostQuery;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.search.BooleanClause.Occur;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;

import static io.anserini.search.SearchCollection.BREAK_SCORE_TIES_BY_DOCID;

public class Simulator {
	
	private IndexReader reader;
	private IndexSearcher searcher;
	private HashMap<String, HashMap<String, ArrayList<String>>> clusters;
	private IndexUtils utils;
	private QueryCreator creator;
	private RelevanceModel rm;
	private HashMap<String, Double> fields;
	private 	HashMap<String, String> contentFields;
	
	public Simulator(String indexDir, String stopwordDir, String clustersDir, HashMap<String, Double> inputFields, String rmField, 
			HashMap<String, String> contentFieldsInput) throws IOException {
		Path p = Paths.get(indexDir);
		Directory indexDirectory = FSDirectory.open(p);
		reader = DirectoryReader.open(indexDirectory);
		searcher = new IndexSearcher(reader);
		searcher.setSimilarity(new BM25Similarity(0.9f, 0.4f));
		clusters = parseClustersFile(clustersDir);
		utils = new IndexUtils(indexDir, stopwordDir);
		creator = new QueryCreator(utils);
		rm = new RelevanceModel(searcher, creator, reader, rmField);
		fields = inputFields;
		contentFields = contentFieldsInput;
	}
	
	public HashMap<String, HashMap<String, ArrayList<String>>> parseClustersFile(String clustersDir) {
		HashMap<String, HashMap<String, ArrayList<String>>> clusters = new HashMap<>(); // query -> cluster -> [documents]
		
		ArrayList<String> lines = Utils.readLinesFromFile(clustersDir);
		for(String line : lines) {
			String[] args = line.split(" ");
			String qid = args[0];
			String clusterId = args[1];
			String docid = args[2];
			
			if(!clusters.containsKey(qid)) {
				clusters.put(qid, new HashMap<>());
				clusters.get(qid).put("all", new ArrayList<>());
			}
			if(!clusters.get(qid).containsKey(clusterId)) {
				clusters.get(qid).put(clusterId, new ArrayList<>());
			}
			clusters.get(qid).get(clusterId).add(docid);
			clusters.get(qid).get("all").add(docid);
		}
		return clusters;
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
	
	public double getClusterSize(String qid, String clusterId) {
		return clusters.get(qid).get(clusterId).size();
	}
	
	public int getNumRelevant(String qid) {
		return clusters.get(qid).get("all").size();
	}
	
	public ArrayList<String> getRelDocuments(ArrayList<String> documentIds, String qid) {
		ArrayList<String> relDocs = new ArrayList<>();
		for(String docId : documentIds) {
			if(clusters.get(qid).get("all").contains(docId)) {
				relDocs.add(docId);
			}
		}
		return relDocs;
	}
	
	public int getNumberOfClusters(String qid) {
		return clusters.get(qid).size();
	}
	
	public double getQueryAspectScore(ArrayList<String> words, String qid, ArrayList<String> relDocs) throws IOException {
		double score = 0.0;
		for(String word : words) {
			score += getWordScore(word, qid, "all", relDocs);
		}
		return score / ((double) words.size());
	}
	
	public double getWordScore(String word, String qid, String clusterId, ArrayList<String> relDocs) throws IOException {
		double tf = 0.0;
		String stemmedWord = utils.analyzeText(word);
		if(!clusters.containsKey(qid))
			return 0.0;
		if(!clusters.get(qid).containsKey(clusterId))
			return 0.0;
		for(String docId : clusters.get(qid).get(clusterId)) {
			if(!relDocs.contains(docId)) {
				HashMap<String, Double> docVector  = utils.getTfVectorFromTrecId(docId);
				tf += docVector.getOrDefault(stemmedWord, 0.0);
			}
		}
		tf = Math.log(1 + tf);		
		double idf = utils.getIdf(stemmedWord, "titleabstract");
		//System.out.println(word + " " + tf + " " + idf);
		return tf;
	}
	
	public String getTRECFormat(TopDocs docs, String qid, String runName) throws IOException {
		String output = "";
		ScoreDoc[] results = docs.scoreDocs;
		for(int i = 0 ; i < results.length; i++) {
			Document hitDoc = searcher.doc(results[i].doc);
			String docno = hitDoc.get("id");
			Float score = results[i].score;
			int rank = i+1;
			output += qid + " Q0 " + docno + " " + rank + " " + score + " " + runName + "\n";
		}
		return output;
	}
	
	public String search(String qid, String query, ArrayList<String> expansionTerms, 
			ArrayList<Double> expansionWeights, double queryWeight, boolean processQuery, boolean processExpansion, String runName) throws IOException {
		Query q = creator.buildExpandedQuery(expansionTerms, expansionWeights, query, fields, queryWeight, processQuery, processExpansion);
		System.out.println(q);
		TopDocs docs = searcher.search(q, 1000);
		//TopDocs docs = searcher.search(q, 1000, BREAK_SCORE_TIES_BY_DOCID, true);
		String trecOutput = getTRECFormat(docs, qid, runName);
		return trecOutput;
	}
	
	public ArrayList<HashMap<String,String>> searchGetText(String qid, String query, ArrayList<String> expansionTerms, 
			ArrayList<Double> expansionWeights, double queryWeight, int numDocs, boolean processQuery, boolean processExpansion) throws IOException {
		
		ArrayList<HashMap<String,String>> docFields = new ArrayList<>();
		Query q = creator.buildExpandedQuery(expansionTerms, expansionWeights, query, fields, queryWeight, processQuery, processExpansion);
		System.out.println(q);
		//TopDocs docs = searcher.search(q, numDocs, BREAK_SCORE_TIES_BY_DOCID, true);
		TopDocs docs = searcher.search(q, numDocs);
		ScoreDoc[] results = docs.scoreDocs;
		
		int limit = numDocs;
		if(results.length < numDocs) {
			limit = results.length;
		}
		
		for (int i = 0 ; i < limit; i++) {
			HashMap<String,String> outputMap = new HashMap<>();
			Document hitDoc = searcher.doc(results[i].doc);
			String text = hitDoc.get(contentFields.get("textField"));
			String docId = hitDoc.get(contentFields.get("idField"));
			String title = hitDoc.get(contentFields.get("titleField"));
			
			String relevance = "Not Relevant";
			String relCluster = "0";
			
			
			if(clusters.containsKey(qid)) {
				for (String clusterId : clusters.get(qid).keySet()) {
					
					if(clusters.get(qid).get(clusterId).contains(docId)) {
						relevance = "Relevant";
						relCluster = clusterId;
						break;
					}
				}
			}
			
			outputMap.put("relevance", relevance);
			outputMap.put("cluster", relCluster);
			outputMap.put("id", docId);
			outputMap.put("text", text);
			outputMap.put("title", title);
			docFields.add(outputMap);
		}
		
		return docFields;
	}
	
	public String getClusterDistribution(String qid, ArrayList<String> docIds) {
		String outputLine = "";
		HashMap<String, Integer> clusterCounters = new HashMap<>();
		
		for (String clusterId : clusters.get(qid).keySet()) {
			clusterCounters.put(clusterId, 0);
		}
		
		if(clusters.containsKey(qid)) {
			for (String id : docIds) {
				for (String clusterId : clusters.get(qid).keySet()) {
					if(clusters.get(qid).get(clusterId).contains(id)) {
						clusterCounters.put(clusterId, clusterCounters.get(clusterId) + 1);
						break;
					}
				}
			}
			
			Integer overall = 0;
			Integer overallRel = 0;
			for(String clusterId : clusters.get(qid).keySet()) {
				outputLine += clusterId + ": "+ Integer.toString(clusterCounters.get(clusterId));
				outputLine += "/" + Integer.toString(clusters.get(qid).get(clusterId).size()) + ", ";
				
				overall += clusters.get(qid).get(clusterId).size();
				overallRel += clusterCounters.get(clusterId);
			}
			outputLine += "overall" + ": "+ Integer.toString(overallRel);
			outputLine += "/" + Integer.toString(overall);
		}
		return outputLine;
	}
	
	public ArrayList<Integer> getTopDocs(String query, ArrayList<String> expansionTerms, 
			ArrayList<Double> expansionWeights, double queryWeight, int numDocs, boolean processQuery, boolean processExpansion) throws IOException {
		ArrayList<Integer> docIds = new ArrayList<>();
		Query q = creator.buildExpandedQuery(expansionTerms, expansionWeights, query, fields, queryWeight, processQuery, processExpansion);
		TopDocs docs = searcher.search(q, numDocs);
		ScoreDoc[] results = docs.scoreDocs;
		
		int limit = numDocs;
		if(results.length < numDocs) {
			limit = results.length;
		}
		
		for (int i = 0 ; i < limit; i++) {
			docIds.add(results[i].doc);
		}
		
		return docIds;
	}
	 
	public HashMap<String, Double> getRm3Terms(String query, Double anchorWeight, int numDocs, int numTerms) throws IOException {
		HashMap<String, Double> origQuery = creator.getOrigQueryLM(query);
		HashMap<String, Double> rm1 = rm.getRmVec(query, numDocs, numTerms, fields);
		HashMap<String, Double> rm3 = new HashMap<>();
		
		for(String t : origQuery.keySet()) {
			rm3.put(t, anchorWeight * origQuery.get(t) + (1-anchorWeight) * rm1.getOrDefault(t, 0.0));
		}
		
		for(String t : rm1.keySet()) {
			if(!origQuery.containsKey(t)) {
				rm3.put(t, (1-anchorWeight) * rm1.get(t));
			}
		}
		return rm3;
	}
	
	public HashMap<String, Double> getRm1Terms(String query, Double anchorWeight, int numDocs, int numTerms) throws IOException {
		HashMap<String, Double> rm1 = rm.getRmVec(query, numDocs, numTerms, fields);
		return rm1;
	}
	
	public HashMap<String, Double> getRm1IterativeTerms(String query, ArrayList<String> terms, ArrayList<Double> weights, 
			Double anchorWeight, int numDocs, int numTerms) throws IOException {
		
		Query q = creator.buildExpandedQuery(terms, weights, query, fields, anchorWeight, true, true);
		HashMap<String, Double> rm1 = rm.getRmVecIterative(q, numDocs, numTerms);
		return rm1;
	}
	
	public String reRank(String qid, String query, ArrayList<String> expansionTerms, ArrayList<Double> expansionWeights, 
			boolean processQuery, boolean processExpansion, String runName) throws IOException {
		
		Query originalQuery = creator.buildExpandedQuery(new ArrayList<>(), new ArrayList<>(), query, fields, 1.0, processQuery, processExpansion);
		Query expansionQuery = creator.buildExpandedQuery(expansionTerms, expansionWeights, query, fields, 0.0, processQuery, processExpansion);
		//System.out.println(expansionQuery);
		TopDocs docs = searcher.search(originalQuery, 1000, BREAK_SCORE_TIES_BY_DOCID, true);
		ScoreDoc[] results = docs.scoreDocs;
		ArrayList<String> idsList = new ArrayList<>();

		for(int i = 0 ; i < results.length; i++)
		{
			int docId = results[i].doc;
			Document hitDoc = searcher.doc(docId);
			idsList.add(hitDoc.get("id"));
			//#Explanation explain = searcher.explain(expansionQuery, docId);
			//Float score = (Float) explain.getValue();
			//reRankedList.put(docId, score);
		}
		
		
		
		BooleanQuery.Builder idQueryBuilder = new BooleanQuery.Builder();
		for(String id : idsList)
		{
			Term t = new Term("id", id);
			BoostQuery boostQuery = new BoostQuery(new TermQuery(t), 0f);
			BooleanClause booleanClause = new BooleanClause(boostQuery, Occur.SHOULD);
			idQueryBuilder.add(booleanClause);
		}
		
		Query idQuery = idQueryBuilder.build();
		BooleanQuery.Builder finalQueryBuilder = new BooleanQuery.Builder();
		finalQueryBuilder.add(idQuery, Occur.MUST);
		finalQueryBuilder.add(expansionQuery, Occur.SHOULD);
		Query finalQuery = finalQueryBuilder.build();
		TopDocs res = searcher.search(finalQuery, 1000, BREAK_SCORE_TIES_BY_DOCID, true);
		System.out.println(finalQuery);
		String trecOutput = getTRECFormat(res, qid, runName);
		
		/*
		String output = "";
		Map<Integer,Float> sortedMap = Utils.sortByValue(reRankedList);
		int rank = 1;
		for(Integer docId : sortedMap.keySet()) {
			Document hitDoc = searcher.doc(docId);
			String docno = hitDoc.get("id");
			Float score = sortedMap.get(docId);
			output += qid + " Q0 " + docno + " " + rank + " " + score + " uiuc\n";
			rank += 1;
		}
		*/
		return trecOutput;
	}
	
 	public static void main(String[] args) throws IOException {
		String indexDir = "/Users/saarkuzi/Documents/java_workspace/anserini/lucene-index.robust04.krovetz.pos+docvectors+rawdocs";
		//String indexDir = "/home/skuzi2/kb-explorer/lucene-index.robust04.krovetz.pos+docvectors+rawdocs";
  		String stopwordDir = "/Users/saarkuzi/Documents/java_workspace/fig-search/lemur-stopwords.txt";
  		//String stopwordDir = "/home/skuzi2/kb-explorer/lemur-stopwords.txt";
  		String clustersDir = "clusters.txt";
  		//String clustersDir = "/home/skuzi2/kb-explorer/clusters.txt";
  		HashMap<String, Double> fields = new HashMap<>();
  		fields.put("title", 1.0);
  		fields.put("abstract", 1.0);
  		HashMap<String, String> contentFields = new HashMap<>();
  		contentFields.put("textField", "raw");
  		contentFields.put("titleField", "id");
  		contentFields.put("idField", "id");
  		Simulator s = new Simulator(indexDir, stopwordDir, clustersDir, fields, "contents", contentFields);	
	}
}
