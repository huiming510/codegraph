package jp.co.rct.jj.action;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;

import jp.co.rct.jj.base.service.JJFileManagerService;
import jp.co.rct.jj.form.JJ901APITEST001Form;
import r2framework.core.util.R2Date;

public class JJ901APITEST001Action {

	/** アクションフォーム */
	@ActionForm
	@Resource(name = "JJ901APITEST001Form")
	private JJ901APITEST001Form form;

	@Resource
	private R2Date r2Date;

	/** ファイルマネージャサービス */
	@Resource(name = "JJFileManagerService")
	private JJFileManagerService fileManager;

	/** メッセージ表示用 */
	public String dispMessage = "";

	/** テスト実行ステータス -1:実行中 0:未実行 1:実行完了 2:他の人が実行中 */
	public int resultStatus = 0;

	/** テスト実施環境 */
	public String testEnv = "";

	/** テスト実施API */
	public String testAPI = "";

	/** テスト実行コマンドパス */
	public final String commandPath = "/web/dbhome/jj3/work/nri/api-test/bin/api-test.csh";

	/** ステータスファイルパス */
	public final String STATUS_FILE = "/web/dbhome/jj3/work/nri/api-test/bin/api-test.sts";

	/** 実行結果htmlパス */
	public final String resultHtmlPath_bknapi = "/web/hthome/jj3/api-test-chintai/bknapi_3_result";
	public final String resultHtmlPath_shsapi = "/web/hthome/jj3/api-test-chintai/shsapi_3_result";
	public final String resultHtmlPath_cstapi = "/web/hthome/jj3/api-test-chintai/cstapi_3_result";
	/** 表示用APIテスト結果ファイル名 */
	public String resultHtmlName = "";

	/** テスト実行用コマンド **/
	public String[] executeCommand;

	/** 表示用APIテスト実行結果htmlファイル名 */
	public String resultHtmlName_bknapi = "";
	public String resultHtmlName_shsapi = "";
	public String resultHtmlName_cstapi = "";

	/** 前回テスト時間 */
	public String lastDateTime_bknapi = "";
	public String lastDateTime_shsapi = "";
	public String lastDateTime_cstapi = "";

	/** _response */
	public HttpServletResponse response;

	/** _request */
	public HttpServletRequest request;

	/**
	 * 初期表示画面
	 */
	@Execute(validator = false)
	public String index() {

		// 前回結果のテスト結果htmlが存在している場合はファイル名を取得して前回テスト実行日時を取得する
		if (getFileName(resultHtmlPath_bknapi).equals("－")) {
			lastDateTime_bknapi = getFileName(resultHtmlPath_bknapi);
		} else {
			lastDateTime_bknapi = getLastDateTime(getFileName(resultHtmlPath_bknapi));
		}

		if (getFileName(resultHtmlPath_shsapi).equals("－")) {
			lastDateTime_shsapi = getFileName(resultHtmlPath_shsapi);
		} else {
			lastDateTime_shsapi = getLastDateTime(getFileName(resultHtmlPath_shsapi));
		}

		if (getFileName(resultHtmlPath_cstapi).equals("－")) {
			lastDateTime_cstapi = getFileName(resultHtmlPath_cstapi);
		} else {
			lastDateTime_cstapi = getLastDateTime(getFileName(resultHtmlPath_cstapi));
		}

		return "JJ901APITEST00101.jsp";
	}

	// パスを受け取り、その配下にファイルが1つだけあればファイル名を返す
	public String getFileName(String path) {

		// 引数のパスにファイルが存在するかを確認
		File dir = new File(path);
		File[] list = dir.listFiles();

		switch (list.length) {
			case 1:
				// ファイルが存在する場合は、前回結果を表出する
				return list[0].getName();

			default:
				// ファイルが無い、もしくは2個以上ある場合は前回日時を「－」とする
				return "－";
		}
	}

	/**
	 * テスト実行表示画面
	 */
	@Execute(validator = false)
	public String execute() {

		try {
			String status = checkStatus();

			// ステータスが実行中だった場合は、エラーとする
			if (status.equals("RUNNING")) {

				dispMessage = "他の人がテスト実行中です。時間を空けて再度実行してください。";
				resultStatus = 2;

				return "JJ901APITEST00101.jsp";
			}

			// テスト対象を取得しコマンドを生成
			testEnv = form.env;
			testAPI = form.api;
			executeCommand = new String[] {
					"tcsh", commandPath, testAPI, testEnv };

			/*
			 * テスト実行用スレッドを作成し走らせる
			 * 非同期処理のため、バックグラウンドでテストが実行される
			 */
			Thread thread = new Thread(new TestExecuter());
			thread.start();

			// ステータスを実行中にして、返却する
			resultStatus = -1;
			dispMessage = "テスト実行中です。完了までしばらくお待ちください。（※このページは10秒ごとに自動更新します）";

			return "JJ901APITEST00101.jsp";

		} catch (FileNotFoundException e1) {

			dispMessage = "ステータスファイルがありません。確認してください。";
			resultStatus = 0;
			return "JJ901APITEST00101.jsp";

		} catch (IOException e) {

			dispMessage = "システムエラーが発生しました。";
			resultStatus = 0;
			return "JJ901APITEST00101.jsp";

		}
	}

	/**
	 * ステータスファイルの確認
	 *
	 * @throws IOException
	 */
	private String checkStatus() throws FileNotFoundException, IOException {

		//クラスライブラリの呼び出し
		BufferedReader br;

		br = new BufferedReader(
				new InputStreamReader(new FileInputStream(STATUS_FILE)));

		// ステータスファイルの内容を読みむ
		String sts = br.readLine();
		br.close();

		return sts;
	}

	/**
	 * テスト実行シェルのキック
	 */
	private class TestExecuter implements Runnable {
		/*
		 * (非 Javadoc)
		 *
		 * @see java.lang.Runnable#run()
		 */
		@Override
		public void run() {

			// テスト実行シェルをキック
			try {

				Process process = Runtime.getRuntime().exec(executeCommand);

				// 子プロセスの終了を待つ
				process.waitFor();

				// 子プロセスを明示的に終了させ、資源を回収できるようにする
				process.destroy();

			} catch (IOException e) {
			} catch (InterruptedException e) {
			}
		}

	}

	/**
	 * 比較結果htmlダウンロード_物件検索API（V4）
	 */
	@Execute(validator = false)
	public String downloadBknapi() {

		// テスト結果htmlが存在している場合はファイル名を取得する
		File dir = new File(resultHtmlPath_bknapi);
		File[] list = dir.listFiles();

		switch (list.length) {
			case 0:
				// ファイルが無い場合は、エラーメッセージを表示する
				resultStatus = 0;
				dispMessage = "ダウンロードできるファイルがありません";
				return "JJ901APITEST00101.jsp";

			case 1:
				// ファイルが存在する場合は。ファイル名を取得してダウンロードを実行する
				resultHtmlName_bknapi = list[0].getName();
				outputFile(request, response, resultHtmlPath_bknapi + "/" + resultHtmlName_bknapi);

				return null;

			default:
				dispMessage = "結果出力フォルダに2個以上のファイルがあります。確認してください。";
				resultStatus = 0;
				return "JJ901APITEST00101.jsp";
		}
	}

	/**
	 * 比較結果htmlダウンロード_賃貸詳細API
	 */
	@Execute(validator = false)
	public String downloadShsapi() {

		// テスト結果htmlが存在している場合はファイル名を取得する
		File dir = new File(resultHtmlPath_shsapi);
		File[] list = dir.listFiles();

		switch (list.length) {
			case 0:
				// ファイルが無い場合は、エラーメッセージを表示する
				resultStatus = 0;
				dispMessage = "ダウンロードできるファイルがありません";
				return "JJ901APITEST00101.jsp";

			case 1:
				// ファイルが存在する場合は。ファイル名を取得してダウンロードを実行する
				resultHtmlName_shsapi = list[0].getName();
				outputFile(request, response, resultHtmlPath_shsapi + "/" + resultHtmlName_shsapi);

				return null;

			default:
				dispMessage = "結果出力フォルダに2個以上のファイルがあります。確認してください。";
				resultStatus = 0;
				return "JJ901APITEST00101.jsp";
		}
	}

	/**
	 * 比較結果htmlダウンロード_賃貸カセットAPI
	 */
	@Execute(validator = false)
	public String downloadCstapi() {

		// テスト結果htmlが存在している場合はファイル名を取得する
		File dir = new File(resultHtmlPath_cstapi);
		File[] list = dir.listFiles();

		switch (list.length) {
			case 0:
				// ファイルが無い場合は、エラーメッセージを表示する
				resultStatus = 0;
				dispMessage = "ダウンロードできるファイルがありません";
				return "JJ901APITEST00101.jsp";

			case 1:
				// ファイルが存在する場合は。ファイル名を取得してダウンロードを実行する
				resultHtmlName_cstapi = list[0].getName();
				outputFile(request, response, resultHtmlPath_cstapi + "/" + resultHtmlName_cstapi);

				return null;

			default:
				dispMessage = "結果出力フォルダに2個以上のファイルがあります。確認してください。";
				resultStatus = 0;
				return "JJ901APITEST00101.jsp";
		}
	}

	/**
	 * ファイルをダウンロードできるようにする
	 */
	public void outputFile(HttpServletRequest req, HttpServletResponse res, String filePath) {

		File outputFile = new File(filePath);

		try {
			OutputStream os = res.getOutputStream();

			FileInputStream fis = new FileInputStream(outputFile);
			BufferedInputStream bis = new BufferedInputStream(fis);

			//レスポンス設定
			res.setContentType("application/octet-stream");
			res.setHeader("Content-Disposition", "filename=\"" + outputFile.getName() + "\"");

			int len = 0;
			byte[] buffer = new byte[1024];
			while ((len = bis.read(buffer)) >= 0) {
				os.write(buffer, 0, len);
			}

			bis.close();

		} catch (IOException e) {
		}

	}

	/**
	 * 自動画面リロード用メソッド
	 */
	@Execute(urlPattern = "reload", validator = false)
	public String autoReload() {

		// ステータスを確認する
		String status;
		try {
			status = checkStatus();

			if (status.equals("RUNNING")) {

				dispMessage = "テスト実行中です。完了までしばらくお待ちください。（※このページは10秒ごとに自動更新します）";
				resultStatus = -1;
				return "JJ901APITEST00101.jsp";

			} else {

				/**
				 * 各API比較結果のうち、最も新しいファイルを画面に出力する
				 */
				resultHtmlName = getLatestResult();

				// テスト結果htmlが存在している場合はファイル名を取得して最新のテスト実行日時を取得する
				if (getFileName(resultHtmlPath_bknapi).equals("－")) {
					lastDateTime_bknapi = getFileName(resultHtmlPath_bknapi);
				} else {
					lastDateTime_bknapi = getLastDateTime(getFileName(resultHtmlPath_bknapi));
				}

				if (getFileName(resultHtmlPath_shsapi).equals("－")) {
					lastDateTime_shsapi = getFileName(resultHtmlPath_shsapi);
				} else {
					lastDateTime_shsapi = getLastDateTime(getFileName(resultHtmlPath_shsapi));
				}

				if (getFileName(resultHtmlPath_cstapi).equals("－")) {
					lastDateTime_cstapi = getFileName(resultHtmlPath_cstapi);
				} else {
					lastDateTime_cstapi = getLastDateTime(getFileName(resultHtmlPath_cstapi));
				}
			}

			if (status.equals("FAILED")) {

				dispMessage = "テスト実行に失敗しました。logファイルを確認してください。";
				resultStatus = 0;
				return "JJ901APITEST00101.jsp";
			}

			dispMessage = "テスト完了しました！";
			resultStatus = 1;

			return "JJ901APITEST00101.jsp";

		} catch (FileNotFoundException e) {

			dispMessage = "ステータスファイルがありません。確認してください。";
			resultStatus = 0;

			return "JJ901APITEST00101.jsp";
		} catch (IOException e) {

			dispMessage = "システムエラーが発生ししました。";
			resultStatus = 0;

			return "JJ901APITEST00101.jsp";
		}
	}

	/**
	 * 比較結果htmlファイルの中から最もタイムスタンプが新しいファイルを返す
	 */
	public String getLatestResult() {
		// 初期化
		long timestamp_bknapi = 0;
		long timestamp_shsapi = 0;
		long timestamp_cstapi = 0;

		// ファイル名取得
		String bknapi_result_name = getFileName(resultHtmlPath_bknapi);
		String shsapi_result_name = getFileName(resultHtmlPath_shsapi);
		String cstapi_result_name = getFileName(resultHtmlPath_cstapi);

		// ファイルが存在していたらタイムスタンプを取得
		if (!bknapi_result_name.equals("－")) {

			timestamp_bknapi = getTimeStamp(bknapi_result_name);
		}
		if (!shsapi_result_name.equals("－")) {

			timestamp_shsapi = getTimeStamp(shsapi_result_name);
		}
		if (!cstapi_result_name.equals("－")) {

			timestamp_cstapi = getTimeStamp(cstapi_result_name);
		}

		// タイムスタンプが最も新しいファイルのパスを返す
		if (timestamp_bknapi > timestamp_shsapi && timestamp_bknapi > timestamp_cstapi) {

			return "bknapi_3_result/" + bknapi_result_name;

		} else if (timestamp_shsapi > timestamp_bknapi && timestamp_shsapi > timestamp_cstapi) {

			return "shsapi_3_result/" + shsapi_result_name;

		} else {

			return "cstapi_3_result/" + cstapi_result_name;
		}
	}

	/**
	 * 比較結果htmlファイル名から前回テスト実行日時を取得する
	 */
	public String getLastDateTime(String resultHtmlName) {

		// 比較結果htmlファイルをアンダーバーで区切り、3要素目と4要素目から前回実行日時を取得する
		String[] dateList = resultHtmlName.split("_", -1);
		String date = dateList[2];
		String time = dateList[3].replace(".html", "");

		String dateTime = date.substring(0, 4) + "年" + date.substring(4, 6) + "月" + date.substring(6) + "日 "
				+ time.substring(0, 2) + "時" + time.substring(2, 4) + "分" + time.substring(4) + "秒";

		return dateTime;

	}

	/**
	 * 比較結果htmlファイル名から前回テスト実行日時を取得する
	 */
	public long getTimeStamp(String resultHtmlName) {

		// 比較結果htmlファイルをアンダーバーで区切り、3要素目と4要素目から前回実行日時を取得する
		String[] dateList = resultHtmlName.split("_", -1);
		String date = dateList[2];
		String time = dateList[3].replace(".html", "");

		return Long.parseLong(date + time);

	}

}
