import java.io.IOException;
import java.util.HashMap;

import py4j.GatewayServer;

public class Server {
	
	private Simulator simulator;
	
	public Server(String indexDir, String stopwordDir, String clustersDir, HashMap<String, Double> fields, String rm3Field, HashMap<String, String> contentFields) throws IOException {
		simulator = new Simulator(indexDir, stopwordDir, clustersDir, fields, rm3Field, contentFields);
	}
	
	public Simulator getSimulator() {
		return simulator;
	}
	
 	public static void main(String[] args) throws IOException {
		//String indexDir = "/Users/saarkuzi/Documents/java_workspace/anserini/lucene-index.robust04.krovetz.pos+docvectors+rawdocs";
		//String indexDir = "/home/skuzi2/kb-explorer/lucene-index.robust04.krovetz.pos+docvectors+rawdocs";
 		String localDir = "/Users/saarkuzi/acl_retrieval_collection/";
 		String dataDir = "/home/skuzi2/kb-explorer/";
 		
 		String indexDir = localDir + "/index/";
  		String stopwordDir = localDir + "/lemur-stopwords.txt";
  		//String stopwordDir = "/home/skuzi2/kb-explorer/lemur-stopwords.txt";
  		//String clustersDir = "clusters.txt";
  		String clustersDir = localDir + "/qrels.txt";
  		
  		//String clustersDir = "/home/skuzi2/kb-explorer/clusters.txt";
  		
  		HashMap<String, Double> fields = new HashMap<>();
  		fields.put("title", 0.5);
  		fields.put("abstract", 0.5);
  		String rm3Field = "titleabstract";
  		HashMap<String, String> contentFields = new HashMap<>();
  		contentFields.put("textField", "abstract");
  		contentFields.put("titleField", "title");
  		contentFields.put("idField", "id");
  		
		GatewayServer gatewayServer = new GatewayServer(new Server(indexDir, stopwordDir, clustersDir, fields, rm3Field, contentFields), 24000);
        gatewayServer.start();
        System.out.println("Gateway Server Started");
 	}
}
