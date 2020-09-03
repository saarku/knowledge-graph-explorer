import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.CharArraySet;
import org.apache.lucene.analysis.TokenStream;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.document.Document;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;

import io.anserini.analysis.EnglishStemmingAnalyzer;

/**
 * This class performs different functions using a documents index
 */
public class IndexUtils {
	private IndexReader reader;
	private Analyzer analyzer;
	private IndexSearcher searcher;
	
	public IndexUtils(String indexDir, String stopwordDir) throws IOException {
		Path p = Paths.get(indexDir);
		Directory indexDirectory = FSDirectory.open(p);
		reader = DirectoryReader.open(indexDirectory);
		CharArraySet stopwords = Utils.loadStopwords(stopwordDir);
		analyzer = new EnglishKrovetzAnalyzer(stopwords);
		//analyzer = new EnglishStemmingAnalyzer("porter");
		searcher = new IndexSearcher(reader);
	}
	
	public Analyzer getAnalyzer() {
		return analyzer;
	}
	
	
	/**
	 * Tokenize and pre-process a piece of text
	 * @param docContent   the original text
	 * @return the processed text
	 * @throws IOException
	 */
	public  String processDoc(String docContent) throws IOException {
		TokenStream tokenStream = analyzer.tokenStream("temp", docContent);
		CharTermAttribute charTermAttribute = tokenStream.addAttribute(CharTermAttribute.class);
		tokenStream.reset();
		String output = "";
		
		while (tokenStream.incrementToken()) {
		    String term = charTermAttribute.toString();
		    output += term + " ";
		}
		
		tokenStream.close();
		return output;
	}
	
	/**
	 * Process all documents in the collection and output them to a file
	 * @param outputDir   the directory for the output file
	 * @throws IOException
	 */
  	public void outputDocToFile(String outputDir) throws IOException {
		int numDocs = reader.maxDoc();
		File fout = new File(outputDir);
		FileOutputStream fos = new FileOutputStream(fout);
		BufferedWriter bw = new BufferedWriter(new OutputStreamWriter(fos));

		for(int docId = 0; docId < numDocs; docId++) {
			Document HitDoc = searcher.doc(docId);
			String content = HitDoc.get("title") + " " + HitDoc.get("abstract");
			String[] words = content.split(" ");
			String limitContent = "";
			
			int i = 0;
			for(String w : words) {
				if(i == 1000)
					break;
				limitContent += w + " ";
				i++;
			}
			
			content = processDoc(limitContent);
			bw.write(content);
			bw.newLine();
		}
		bw.close();
 	}
  	
	/**
	 * Output the DOCNO (TREC id) of the documents in the index
	 * @param outputDir   the directory for the output file
	 * @throws IOException
	 */
  	public void outputIDToFile(String outputDir) throws IOException {
		int numDocs = reader.maxDoc();
		File fout = new File(outputDir);
		FileOutputStream fos = new FileOutputStream(fout);
		BufferedWriter bw = new BufferedWriter(new OutputStreamWriter(fos));

		for(int docId = 0; docId < numDocs; docId++) {
			Document HitDoc = searcher.doc(docId);
			String id = HitDoc.get("id");
			bw.write(id);
			bw.newLine();
		}
		bw.close();
 	}
  	
	/**
	 * Takes the queries of TREC and do stemming for them
	 * @param outputDir   the directory for the output file
	 * @throws IOException
	 */
  	public void analyzeTestQueries(String queriesDir, String outputDir) throws IOException {
  		ArrayList<String> lines = Utils.readLinesFromFile(queriesDir);
  		String qid = "";
  		String query = "";
  		ArrayList<String> outputLines = new ArrayList<>();
  		
  		for (String line : lines) {
  			
  			//number
  			if(line.contains("<num>")) {
  				qid = line.split("<num>")[1].split("</num>")[0];
  				qid = qid.split("Number: ")[1];
  				System.out.println(qid);
  			}
  			
  			if(line.contains("<topic number")) {
  				qid = line.split("=\"")[1].split("\"")[0];
  				qid = qid.split("Number: ")[1];
  				System.out.println(qid);
  			}
  			
  			//text
  			if(line.contains("<text>") ) {
  				query = analyzeText(line.split("\\(")[1].split("\\)")[0].trim());
  				query = line.split("\\(")[1].split("\\)")[0].trim();
  				outputLines.add(qid + ":" + query);
  			}
  			
  			if(line.contains("<title>") ) {
  				query = analyzeText(line.split("<title> ")[1]).trim();
  				//query = line.split("<title> ")[1].trim();
  				outputLines.add(qid + ":" + query);
  			}
  			
  			if(line.contains("<query>") ) {
  				query = line.split("<query>")[1].split("</query>")[0];
  				query = analyzeText(query).trim();
  				outputLines.add(qid + ":" + query);
  			}
  		}
  		Utils.writeLinesToFile(outputLines, outputDir);
  	}
  	
	/**
	 * Get a vector of TF values of words in a document
	 * @param docNumber   the TREC ID of the input document
	 * @return a map between a word and the TF value
	 * @throws IOException
	 */
	public  HashMap<String, Double> getTfVector(Integer docId) throws IOException {
		Document d = reader.document(docId);
		String text = d.get("titleabstract");
		
		HashMap<String, Double> frequencyMap = new HashMap<>();
		TokenStream tokenStream = analyzer.tokenStream("temp", text);
		CharTermAttribute charTermAttribute = tokenStream.addAttribute(CharTermAttribute.class);

		tokenStream.reset();
		while (tokenStream.incrementToken()) {
		    String term = charTermAttribute.toString();
		    
		    if(!frequencyMap.containsKey(term))
		    		frequencyMap.put(term, 1.0);
		    else
		    		frequencyMap.put(term, frequencyMap.get(term) + 1.0);
		}
		tokenStream.close();
		return frequencyMap;
	}
  	
	/**
	 * Get a vector of TF values of words in a document
	 * @param docNumber   the index number of the input document
	 * @return a map between a word and the TF value
	 * @throws IOException
	 */
	public  HashMap<String, Double> getTfVectorFromTrecId(String docNumber) throws IOException {
		Query idQuery = QueryCreator.buildIdQuery(docNumber, "id");
		
		TopDocs docs = searcher.search(idQuery, 1);
		
		ScoreDoc[] results = docs.scoreDocs;
		
		if(results.length == 0) {
			return new HashMap<String, Double>();
		}

		return getTfVector(results[0].doc);
	}
	
	 /** 
	 * Analyze a piece of text
	 * @param text   the original text
	 * @return the analyzed text
	 * @throws IOException
	 */
	public String analyzeText(String text) throws IOException {
		String outputText = "";
		TokenStream tokenStream = analyzer.tokenStream("temp", text);
		CharTermAttribute charTermAttribute = tokenStream.addAttribute(CharTermAttribute.class);
		tokenStream.reset();
		while (tokenStream.incrementToken()) {
		    String term = charTermAttribute.toString();
		    outputText += term + " ";
		}
		tokenStream.close();
		return outputText.trim();
	}
	
	 /** 
	 * Get the IDF of a vocabulary term
	 * @param term   input term
	 * @param field the text field for the IDF calculation
	 * @return the IDF score
	 * @throws IOException
	 */
	public Float getIdf(String term, String field) throws IOException
	{
		Term termInstance = new Term(field, term);  
		Float docCount = (float) reader.docFreq(termInstance);
		Float numDocs = (float) reader.numDocs();
		docCount = (float) Math.max(docCount, 0.01);
		return (float) Math.log(numDocs/docCount);
	}
	
  	public static void main(String[] args) throws IOException {
  		String stopwordDir = "/Users/saarkuzi/Documents/java_workspace/fig-search/lemur-stopwords.txt";
  		String emptyStopwordDir = "empty_stopwords.txt";
  		
  		//String indexDir = "/Users/saarkuzi/Documents/java_workspace/anserini/lucene-index.robust04.pos+docvectors+rawdocs";
  		String indexDir = "/Users/saarkuzi/acl_retrieval_collection/index/";
  		
  		//String queriesDir = "/Users/saarkuzi/help-me-search-data/queries/queriesROBUST.xml";
  		String queriesDir = "/Users/saarkuzi/acl_retrieval_collection/queries.txt";
  		
  		
  		IndexUtils utils = new IndexUtils(indexDir, emptyStopwordDir);
  		
  		
  		//utils.outputIDToFile("ids.txt");
  		utils.analyzeTestQueries(queriesDir, "queries.acl.stemmed.with.stop.txt");
  		//utils.outputDocToFile("acl.title.abstract.lines");
  	}
}
