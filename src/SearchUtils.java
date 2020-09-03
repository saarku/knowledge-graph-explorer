import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import org.apache.lucene.analysis.CharArraySet;

public class SearchUtils {
	
	public String configDir;
	public HashMap<String, String> paramsMap;
	public HashMap<String, ArrayList<String>> fieldInfo;
	
	public SearchUtils(String configDir)
	{
		this.configDir = configDir;
		paramsMap = parseParams(configDir);
		fieldInfo = getFieldsInfo();
	}
	
	public HashMap<String, String> parseParams(String paramsDir)
	{
		HashMap<String,String> params = new HashMap<>();
		try {
			File file = new File(paramsDir);
			FileReader fileReader = new FileReader(file);
			BufferedReader bufferedReader = new BufferedReader(fileReader);
			String line;
			while ((line = bufferedReader.readLine()) != null) {
				String[] args = line.split("=");
				params.put(args[0], args[1]);
			}
				fileReader.close();	
			} catch (IOException e) {
				e.printStackTrace();
			}
		return params;
	}
	
	public HashMap<String, ArrayList<String>> getFieldsInfo()
	{
		HashMap<String, ArrayList<String>> fieldsMap = new HashMap<>();
		
		String fieldsInfo = paramsMap.get("fields");
		if(fieldsInfo == null)
			return fieldsMap;
		
		for(String triple : fieldsInfo.split(";"))
		{	
			String[] singles = triple.split(",");
			fieldsMap.put(singles[0], new ArrayList<>());
			fieldsMap.get(singles[0]).add(singles[1]);
			fieldsMap.get(singles[0]).add(singles[2]);
		}
		return fieldsMap;
	}
	
	public static CharArraySet loadStopwords(String stopwordsFileDir)
	{
		ArrayList<String> stopwordsList = new ArrayList<>();
		try {
				File file = new File(stopwordsFileDir);
				FileReader fileReader = new FileReader(file);
				BufferedReader bufferedReader = new BufferedReader(fileReader);
				String line;
				while ((line = bufferedReader.readLine()) != null) {
					stopwordsList.add(line);
				}	
				fileReader.close();
		} catch (IOException e) {
			e.printStackTrace();
		}
		
		CharArraySet c = new CharArraySet(stopwordsList.size(), true);
		for(String word : stopwordsList)
			c.add(word);
		
		return c;
	}
	
	public static ArrayList<String> readLinesFromFile(String linesDir)
	{
		ArrayList<String> output = new ArrayList<>();
		try {
			File file = new File(linesDir);
			FileReader fileReader = new FileReader(file);
			BufferedReader bufferedReader = new BufferedReader(fileReader);
			String line;
			while ((line = bufferedReader.readLine()) != null) {
				output.add(line);
			}
			fileReader.close();	
		} catch (IOException e) {
			e.printStackTrace();
		}
		return output;
	}
	
	public static void main(String[] args)
	{

	}
}
