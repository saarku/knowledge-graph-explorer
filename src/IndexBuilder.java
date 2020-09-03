import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.ArrayList;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.CharArraySet;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.FieldType;
import org.apache.lucene.document.StringField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexOptions;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.IndexableField;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.search.similarities.Similarity;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;

public class IndexBuilder {
	
	private String dataDir;
	private String indexDir;
	private CharArraySet stopwords;
	private SearchUtils util;
	
	public IndexBuilder(String configDir)
	{
		util = new SearchUtils(configDir);
		dataDir = util.paramsMap.get("dataDir");
		indexDir = util.paramsMap.get("indexDir");
		stopwords = SearchUtils.loadStopwords(util.paramsMap.get("stopwordDir"));
	}
	
 	public void build() throws IOException
	{
		Path p = Paths.get(indexDir);
		Directory indexDirectory = FSDirectory.open(p);
		Analyzer analyzer = new EnglishKrovetzAnalyzer(stopwords);
		IndexWriterConfig conf = new IndexWriterConfig(analyzer);
		Similarity sim = new BM25Similarity();
		conf.setSimilarity(sim);
		IndexWriter writer = new IndexWriter(indexDirectory, conf);
		ArrayList<String> ids = new ArrayList<String>();
		
		try {
				File folder = new File(dataDir);
				File[] listOfFiles = folder.listFiles();
			    for (int i = 0; i < listOfFiles.length; i++) 
			    {
			    		File singleFile = listOfFiles[i];
					FileReader fileReader = new FileReader(singleFile);
					BufferedReader bufferedReader = new BufferedReader(fileReader);
					String line;
					Document document = new Document();
					String id = "";

					while ((line = bufferedReader.readLine()) != null) 
					{
						line = line.replaceAll("\n", "");
						String fieldName = line.split(">")[0].split("<")[1];
						String content = line.split(">")[1].split("<")[0];
						
						if(fieldName.equals("id")) {
							id = content;
						}
												
						if(!util.fieldInfo.containsKey(fieldName))
							continue;
						
						Field.Store store;
						if(util.fieldInfo.get(fieldName).get(1).equals("store"))
							store = Field.Store.YES;
						else
							store = Field.Store.NO;
						
						Field field;
						if(util.fieldInfo.get(fieldName).get(0).equals("string")) {
							field = new StringField(fieldName, content, store);
						}
						else
						{
							FieldType fieldType = new FieldType();
							fieldType.setStored(true);
							fieldType.setStoreTermVectors(true);
							fieldType.setStoreTermVectorPositions(true);
							fieldType.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS);		
							field = new Field(fieldName, content, fieldType);
						}
						
						document.add(field);
					}
					bufferedReader.close();
					
					if(!ids.contains(id)) {
						writer.addDocument(document);
						ids.add(id);
					}
					else {
						System.out.println(id);
					}
			    }
			    writer.close();
		} catch (IOException e) {
			e.printStackTrace();
		}
	}
 	
 	public void checkIndex() throws IOException
 	{
		Path p = Paths.get(util.paramsMap.get("indexDir"));
		Directory indexDirectory = FSDirectory.open(p);
		IndexReader reader = DirectoryReader.open(indexDirectory);
		System.out.println(reader.maxDoc());
		IndexSearcher searcher = new IndexSearcher(reader);
		
		for(int i = 0; i < 5; i++) {
			Document HitDoc = searcher.doc(i);
			
			List<IndexableField> fields = HitDoc.getFields();
			for(IndexableField f : fields)
			{
				String fieldName = f.name();
				String content = HitDoc.get(fieldName);
				System.out.println(fieldName + ": " + content);
			}
		}
 	}
 	
	public static void main(String[] args) throws IOException
	{
		String configDir = "search-engine.conf";
		IndexBuilder builder = new IndexBuilder(configDir);
		builder.build();
	}
}