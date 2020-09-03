import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Map;
import java.util.TreeMap;

import org.apache.lucene.analysis.CharArraySet;

public class Utils {
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
	
	public static void writeLinesToFile(ArrayList<String> lines, String outputDir) throws IOException
	{
		File fout = new File(outputDir);
		FileOutputStream fos = new FileOutputStream(fout);
	 
		BufferedWriter bw = new BufferedWriter(new OutputStreamWriter(fos));
	 
		for (String line : lines) {
			bw.write(line);
			bw.newLine();
		}
		bw.close();
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
	
	public static Map sortByValue(Map unsortedMap)
	{
		Map sortedMap = new TreeMap(new ValueComparator(unsortedMap));
		sortedMap.putAll(unsortedMap);
		return sortedMap;
	}
}

class ValueComparator implements Comparator {
	Map map;
	public ValueComparator(Map map) {
		this.map = map;
	}
	
	public int compare(Object keyA, Object keyB) {
		Comparable valueA = (Comparable) map.get(keyA);
		Comparable valueB = (Comparable) map.get(keyB);
		return valueB.compareTo(valueA);
	}
}
