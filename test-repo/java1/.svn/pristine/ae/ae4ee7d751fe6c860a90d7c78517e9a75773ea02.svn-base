package jp.co.rct.jj.action;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Calendar;
import java.util.Date;
import java.util.List;

import javax.annotation.Resource;

import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;

import jp.co.rct.jj.form.JJ901ESTIMATE001Form;
import r2framework.core.util.R2Date;

public class JJ901ESTIMATE001Action {

	/** アクションフォーム */
	@ActionForm
	@Resource(name = "JJ901ESTIMATE001Form")
	private JJ901ESTIMATE001Form form;

	public String esProcessCompleteTime = "";
	public String dbProcessCompleteTime = "";
	public String keisaiProcessCompleteTime = "";
	public String displayTime = "0:00";
	public String resultJudgmentMessage = "";
	public String startDate = "";
	public String endDate = "";

	private static final String SUCCESS_MESSAGE = "掲載確定の処理完了時刻を算出しました";
	private static final String FAILURE_MESSAGE = "入力不備のため掲載確定の処理完了時刻を算出できませんでした";

	/** 日付取得クラス */
	@Resource
	private R2Date r2Date;

	@Execute(validator = false)
	public String index() {
		getDate();
		return "JJ901ESTIMATE001.jsp";
	}

	/**
	 * 掲載確定の処理時間算出
	 */
	@Execute(validator = false)
	public String estimatedProcessingTime() {

		String bukkenSu = form.bukkenSu;
		String arrivalTime = form.arrivalTime;
		String esJisseki = form.esJisseki;
		String dbJisseki = form.dbJisseki;
		String keisaiJisseki = form.keisaiJisseki;
		String jissekiBukkenSu = form.jissekiBukkenSu;

		//IF到着時刻表示用変数
		double ifArrivalTimeDouble = Double.parseDouble(arrivalTime);
		displayTime = translationDoubleToString(ifArrivalTimeDouble);

		//実績データリスト（処理時間）から実行時間をint型で取得
		List<Integer> esEndProcessTimeList = getEndProcessTime(esJisseki);
		List<Integer> dbEndProcessTimeList = getEndProcessTime(dbJisseki);
		List<Integer> keisaiEndProcessTimeList = getEndProcessTime(keisaiJisseki);

		//実績データ（物件数）のtabと改行をカンマに変換
		jissekiBukkenSu = jissekiBukkenSu.replace("\t", ",");
		jissekiBukkenSu = jissekiBukkenSu.replace("\r\n", ",");

		//実績データ（物件数）の要素をカンマ区切りでListに格納
		List<String> jissekiBukkenSuList = Arrays.asList(jissekiBukkenSu.split(","));

		//実績データ（物件数）からIF到着時間の実績を取得
		List<String> jissekiArriveTimeList = new ArrayList<String>();
		for (int i = 0; i < jissekiBukkenSuList.size(); i++) {
			try {
				int item = 10 * i + 3;
				jissekiArriveTimeList.add(jissekiBukkenSuList.get(item));
			} catch (IndexOutOfBoundsException e) {
				break;
			}
		}

		List<Integer> startProcessTimeList = translationStringToInte(jissekiArriveTimeList);

		//処理完了時間を取得
		List<Integer> esProcessTimeList = getProcessTime(startProcessTimeList, esEndProcessTimeList);
		List<Integer> dbProcessTimeList = getProcessTime(startProcessTimeList, dbEndProcessTimeList);
		List<Integer> keisaiProcessTimeList = getProcessTime(startProcessTimeList, keisaiEndProcessTimeList);

		//実績データ（物件数）から物件数の実績を取得
		List<Integer> jissekiTotalBukkenSu = new ArrayList<Integer>();
		for (int i = 0; i < jissekiBukkenSuList.size(); i++) {
			try {
				int item = 10 * i + 5;
				int jissekiBukkensu = Integer.parseInt(jissekiBukkenSuList.get(item));
				item += 4;
				int jissekiSakujoBukkenSu = 0;
				//削除物件数がNONEの場合は0として計算
				if (!jissekiBukkenSuList.get(item).equals("NONE")) {
					jissekiSakujoBukkenSu = Integer.parseInt(jissekiBukkenSuList.get(item));
				}
				jissekiTotalBukkenSu.add(jissekiBukkensu + jissekiSakujoBukkenSu);
			} catch (IndexOutOfBoundsException e) {
				break;
			}
		}

		//実績データ（物件数）のデータが処理時間かチェック
		List<Integer> bukkenSuDataList = new ArrayList<Integer>();
		for (int i = 0; i < jissekiBukkenSuList.size(); i++) {
			String item = jissekiBukkenSuList.get(i);

			try {
				if (item.contains("分")) {
					//処理時間の後ろのデータを取得
					int tmp = Integer.parseInt(jissekiBukkenSuList.get(i + 1));
					bukkenSuDataList.add(tmp);
				}
			} catch (IndexOutOfBoundsException e) {

			}
		}

		//物件数データチェック
		if (bukkenSuDataCheck(bukkenSu)) {
			resultJudgmentMessage = FAILURE_MESSAGE;
		} else {
			try {
				SimpleDateFormat sdf = new SimpleDateFormat("HH:mm");

				//最小二乗法の計算
				Date esProcessCompleteTimeDate = sdf
						.parse(kaikiChokusen(jissekiTotalBukkenSu, esProcessTimeList, bukkenSu, arrivalTime));
				Date dbProcessCompleteTimeDate = sdf
						.parse(kaikiChokusen(jissekiTotalBukkenSu, dbProcessTimeList, bukkenSu, arrivalTime));
				Date keisaiProcessCompleteTimeDate = sdf
						.parse(kaikiChokusen(jissekiTotalBukkenSu, keisaiProcessTimeList, bukkenSu, arrivalTime));

				esProcessCompleteTime = sdf.format(esProcessCompleteTimeDate);
				dbProcessCompleteTime = sdf.format(dbProcessCompleteTimeDate);
				keisaiProcessCompleteTime = sdf.format(keisaiProcessCompleteTimeDate);

			} catch (ParseException e) {
				resultJudgmentMessage = FAILURE_MESSAGE;
			}
		}
		getDate();

		return "JJ901ESTIMATE001.jsp";
	}

	/**
	 * 現在日付と1ヶ月前の日付を取得
	 */
	private void getDate() {
		SimpleDateFormat sdf = new SimpleDateFormat("yyyy/MM/dd");
		endDate = sdf.format(r2Date.get());
		Calendar calendar = Calendar.getInstance();
		calendar.add(Calendar.MONTH, -1);
		startDate = sdf.format(calendar.getTime());
	}

	/**
	 * 最小二乗法メソッド
	 */
	public String kaikiChokusen(List<Integer> bukkenSuList, List<Integer> shorizikanList, String bukkenSuString,
			String arrivalTimeString) {
		//引数のリストをint型へ変換する
		int arrivalTime = Integer.parseInt(arrivalTimeString);
		int bukkenSu = Integer.parseInt(bukkenSuString);
		int dataSize = 0;

		//データの個数
		if (bukkenSuList.size() < shorizikanList.size()) {
			dataSize = bukkenSuList.size();
		} else {
			dataSize = shorizikanList.size();
		}

		//物件数と処理完了時間のそれぞれの合計と平均
		double sumX = 0;
		double sumY = 0;
		for (int i = 0; i < dataSize; i++) {
			sumX += bukkenSuList.get(i);
			sumY += shorizikanList.get(i);
		}
		double avgX = sumX / dataSize;
		double avgY = sumY / dataSize;

		//偏差積の合計と偏差の合計
		double covXY = 0;
		double varX = 0;
		for (int i = 0; i < dataSize; i++) {
			covXY += (bukkenSuList.get(i) - avgX) * (shorizikanList.get(i) - avgY);
			varX += (bukkenSuList.get(i) - avgX) * (bukkenSuList.get(i) - avgX);
		}

		//傾きを計算
		double slope = covXY / varX;

		//b(切片)の計算
		double intercept = avgY - slope * avgX;

		//物件数から処理完了時間の算出
		double kanryoTime = slope * bukkenSu + intercept;

		//処理完了時間とIF到着時間を加算
		double ansTime = arrivalTime + kanryoTime;

		//加算した値を時刻へ変換
		String time = translationDoubleToString(ansTime);

		return time;
	}

	/**
	 * double型をString型(時刻)に変換
	 */
	public String translationDoubleToString(double doubleData) {

		//時間の算出
		double hh = doubleData / 60;
		//分の算出
		double mm = doubleData % 60;

		//24時間を超えた場合の処理
		while (hh >= 24) {
			hh -= 24;
		}

		//分が1桁の場合、0を先頭に足す
		String minute = ":" + (int) mm;
		if (minute.length() == 2)
			minute = ":0" + (int) mm;

		String stringData = (int) hh + minute;

		return stringData;
	}

	/**
	 * String型(時刻)をint型(分)に変換
	 *
	 * @param stringDataList
	 */
	public List<Integer> translationStringToInte(List<String> stringDataList) {
		List<Integer> processTimeList = new ArrayList<Integer>();

		for (String item : stringDataList) {
			String[] parts = item.split(":");

			int hours = Integer.parseInt(parts[0]);
			int minute = Integer.parseInt(parts[1]);

			int processTime = hours * 60 + minute;
			processTimeList.add(processTime);
		}

		return processTimeList;
	}

	/**
	 * 処理実行時間を算出
	 *
	 * @param startTimeData 処理開始時刻
	 * @param endTimeData 処理終了時刻
	 * @return 処理実行時間
	 */
	public List<Integer> getProcessTime(List<Integer> startTimeData, List<Integer> endTimeData) {

		List<Integer> runTimeList = new ArrayList<Integer>();

		for (int i = 0; i < startTimeData.size(); i++) {
			try {
				runTimeList.add(endTimeData.get(i) - startTimeData.get(i) - 1);
			} catch (IndexOutOfBoundsException e) {
				break;
			}
		}

		return runTimeList;
	}

	/**
	 * 処理完了時間を算出
	 *
	 * @param jisseki テキストエリア内のジョブ実績
	 * @return 実行完了時間
	 */
	public List<Integer> getEndProcessTime(String jisseki) {
		//実績データのtabをカンマに変換
		jisseki = jisseki.replace("\t", ",");

		//実績データの要素をカンマ区切りでListに格納
		List<String> jissekiList = Arrays.asList(jisseki.split(","));

		List<String> jissekiDatelist = new ArrayList<String>();
		for (int i = 0; i < jissekiList.size(); i++) {
			try {
				int item = 5 * i + 2;
				jissekiDatelist.add(jissekiList.get(item));
			} catch (IndexOutOfBoundsException e) {
				break;
			}
		}

		List<String> jissekiTimeList = new ArrayList<String>();
		for (String item : jissekiDatelist) {
			String[] parts = item.split(" ");

			jissekiTimeList.add(parts[1]);
		}

		//実績データリストから実行時間をint型で取得
		List<Integer> endTimeList = translationStringToInte(jissekiTimeList);

		if (endTimeList.size() < 2) {
			resultJudgmentMessage = FAILURE_MESSAGE;
		} else if (!(resultJudgmentMessage.equals(FAILURE_MESSAGE))) {
			resultJudgmentMessage = SUCCESS_MESSAGE;
		}

		return endTimeList;
	}

	/**
	 * 入力チェック
	 *
	 * <pre>
	 * 引数が数値かどうかを確認する
	 * </pre>
	 *
	 * @param bukkenSu 物件数
	 * @return true 数値以外, false 数値のみ
	 */
	public boolean bukkenSuDataCheck(String bukkenSu) {
		//2文字以上の数値
		String regexPattern = "^[0-9]+$";

		boolean numberJudgment = bukkenSu.matches(regexPattern);

		if (bukkenSu.equals("")) {
			return true;
		} else if (numberJudgment == false) {
			return true;
		}

		return false;
	}
}