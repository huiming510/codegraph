package jp.co.rct.jj.action;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.sql.Blob;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletResponse;

import org.apache.commons.io.FileUtils;
import org.apache.commons.io.IOUtils;
import org.apache.commons.lang.StringUtils;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.xssf.streaming.SXSSFWorkbook;
import org.apache.poi.xssf.usermodel.XSSFRichTextString;
import org.seasar.extension.jdbc.util.ConnectionUtil;
import org.seasar.framework.util.ResultSetUtil;
import org.seasar.framework.util.StatementUtil;
import org.seasar.framework.util.StringUtil;
import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;
import org.seasar.struts.util.ResponseUtil;

import jp.co.rct.jj.base.auth.JJMD5;
import jp.co.rct.jj.base.env.EnvValueDefineUtil;
import jp.co.rct.jj.base.service.JJFileManagerService;
import jp.co.rct.jj.form.JJ901SQL001Form;
import r2framework.core.util.R2Date;
import r2framework.extension.csv.io.R2CsvListWriter;

public class JJ901SQL001Action {

	/** アクションフォーム */
	@ActionForm
	@Resource(name = "JJ901SQL001Form")
	private JJ901SQL001Form form;

	@Resource
	private JJMD5 jjmd5;

	@Resource
	private R2Date r2Date;

	/** ファイルマネージャサービス */
	@Resource(name = "JJFileManagerService")
	private JJFileManagerService fileManager;

	/** SQL実行のタイムアウト値 */
	private static final int TIMEOUT_SEC = 60;

	/** メッセージ表示用 */
	public String dispMessage = "";

	/** SQL実行時間 */
	public String sqlExecuteTimeMills;

	/** SQL実行件数 */
	public int resultCount = -1;

	/** 表示用SQL実行結果 */
	public List<String> dispColumnName = new ArrayList<String>();
	public List<List<String>> dispColumnValueList = new ArrayList<List<String>>();

	/**
	 * 初期表示画面
	 */
	@Execute(validator = false)
	public String index() {

		return "JJ901SQL00101.jsp";
	}

	/**
	 * SQL結果表示画面
	 */
	@Execute(validator = false)
	public String select() throws Exception {

		// SQL文のセミコロン除去
		String strSql = removeLastSemicolon(form.sql);

		// ＤＢ接続
		Connection connection = createDBConnection();
		PreparedStatement statement = null;
		ResultSet resultSet = null;
		if (connection == null) {
			return "JJ901SQL00101.jsp";
		}
		connection.setAutoCommit(false);

		try {
			long startTime = System.currentTimeMillis();
			statement = connection.prepareStatement(strSql);
			statement.setQueryTimeout(TIMEOUT_SEC);
			statement.setMaxRows(100);// 取得上限（表示上限）
			resultSet = statement.executeQuery();
			sqlExecuteTimeMills = String.valueOf(System.currentTimeMillis() - startTime);

			// SQL結果カラム名格納
			ResultSetMetaData rsmd = resultSet.getMetaData();
			List<Integer> columnType = new ArrayList<Integer>();
			columnType.add(0); // カラム数と合わせるために、空カラム追加
			for (int i = 1; i <= rsmd.getColumnCount(); i++) {
				dispColumnName.add(rsmd.getColumnName(i));
				columnType.add(rsmd.getColumnType(i));
			}

			// SQL結果レコード格納
			while (resultSet.next()) {
				List<String> resultValueList = new ArrayList<String>();
				for (int j = 1; j <= dispColumnName.size(); j++) {
					resultValueList.add(getResultValue(resultSet, columnType, j));
				}
				dispColumnValueList.add(resultValueList);
			}
			ResultSetUtil.close(resultSet);
			StatementUtil.close(statement);

			// 件数取得 「\n」は、最終行コメントアウト対策
			String strCountSql = "SELECT COUNT(*) FROM ( " + strSql + "\n )";
			statement = connection.prepareStatement(strCountSql);
			resultSet = statement.executeQuery();
			resultSet.next();
			resultCount = resultSet.getInt(1);

		} catch (Exception e) {
			dispMessage = e.getMessage();

		} finally {
			// UPDATE,INSERTを許さない機能のため強制ロールバックを行う
			connection.rollback();

			ResultSetUtil.close(resultSet);
			StatementUtil.close(statement);
			ConnectionUtil.close(connection);
		}

		return "JJ901SQL00101.jsp";
	}

	/**
	 * SQL末尾のセミコロン除去処理(SQL*Plusで実行したSQLをそのまま使えるようにする目的)
	 *
	 * @param sql
	 */
	private String removeLastSemicolon(String sql) {
		String resultStr = sql;
		if (sql != null && sql.length() > 0) {

			String lastStr = sql.substring(sql.length() - 1);

			if (";".equals(lastStr)) {
				resultStr = sql.substring(0, sql.length() - 1);
			}
		}

		return resultStr;
	}

	/**
	 * DB接続処理
	 *
	 * @return
	 * @throws Exception
	 */
	private Connection createDBConnection() throws Exception {

		String strUrl = EnvValueDefineUtil.getValue(form.db + "_" + form.server + "_DBCONNECTINFO_URL");
		String strUser = EnvValueDefineUtil.getValue(form.db + "_" + form.server + "_DBCONNECTINFO_USER");
		String strPassword = EnvValueDefineUtil.getValue(form.db + "_" + form.server + "_DBCONNECTINFO_PASS");

		if (StringUtil.isEmpty(strUrl) || StringUtil.isEmpty(strUser) || StringUtil.isEmpty(strPassword)) {
			dispMessage = "指定された接続先は、設定されていません。";
			return null;
		}

		Class.forName("oracle.jdbc.driver.OracleDriver");
		return DriverManager.getConnection(strUrl, strUser, strPassword);
	}

	/**
	 * SQLデータ出力形式の整形
	 */
	private String getResultValue(ResultSet resultSet, List<Integer> columnType, int j) throws SQLException {

		SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
		switch (columnType.get(j)) {
			case java.sql.Types.TIMESTAMP:
				Date getSQLDate = resultSet.getTimestamp(j);
				return (getSQLDate == null) ? "" : sdf.format(getSQLDate);
			case java.sql.Types.BLOB:
				Blob getSQLBlob = resultSet.getBlob(j);
				return (getSQLBlob == null) ? "" : new String((getSQLBlob).getBytes(1l, 2000));
			default:
				return resultSet.getString(j);
		}
	}

	/**
	 * SQL実行計画表示
	 */
	@Execute(validator = false)
	public String autotrace() throws Exception {

		// SQL文のセミコロン除去
		String strSql = removeLastSemicolon(form.sql);

		// ＤＢ接続
		Connection connection = createDBConnection();
		PreparedStatement statement = null;
		ResultSet resultSet = null;
		if (connection == null) {
			return "JJ901SQL00101.jsp";
		}
		connection.setAutoCommit(false);

		try {
			long startTime = System.currentTimeMillis();
			statement = connection.prepareStatement("explain plan for " + strSql);
			statement.setQueryTimeout(TIMEOUT_SEC);
			statement.execute();
			sqlExecuteTimeMills = String.valueOf(System.currentTimeMillis() - startTime);

			statement = connection.prepareStatement("SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY())");
			resultSet = statement.executeQuery();

			// SQL結果カラム名格納
			while (resultSet.next()) {
				// 区切り文字不要のためスキップ
				String columnValues = resultSet.getString(1);
				if (StringUtils.isBlank(columnValues) || StringUtils.indexOf(columnValues, "----") >= 0) {
					continue;
				}
				// cost
				if (StringUtils.indexOf(columnValues, "Id") >= 0) {
					for (String columnName : StringUtils.split(columnValues, "|")) {
						dispColumnName.add(columnName.trim());
					}
					break;
				}
			}

			// SQL結果レコード格納
			while (resultSet.next()) {
				List<String> resultValueList = new ArrayList<String>();

				// 区切り文字不要のためスキップ
				String columnValues = resultSet.getString(1);
				if (StringUtils.isBlank(columnValues) || StringUtils.indexOf(columnValues, "----") >= 0) {
					continue;
				}

				int columnCnt = 1;
				for (String columnValue : StringUtils.split(columnValues, "|")) {
					if (columnCnt == 2) {
						// Operationのみインデントが必要なため、全角スペースで代用
						resultValueList.add(columnValue.replaceAll(" ", "　"));
					} else {
						resultValueList.add(columnValue.trim());
					}
					columnCnt++;
				}

				dispColumnValueList.add(resultValueList);
			}

			// 結果0件だと誤認しそうなので。
			resultCount = 1;

		} catch (Exception e) {
			dispMessage = e.getMessage();

		} finally {
			// UPDATE,INSERTを許さない機能のため強制ロールバックを行う
			connection.rollback();

			ResultSetUtil.close(resultSet);
			StatementUtil.close(statement);
			ConnectionUtil.close(connection);
		}

		return "JJ901SQL00101.jsp";
	}

	/**
	 * ファイルダウンロード処理
	 *
	 * @return
	 * @throws Exception
	 */
	@Execute(validator = false)
	public String fileDownload() throws Exception {

		// SQL文のセミコロン除去
		String strSql = removeLastSemicolon(form.sql);

		// ＤＢ接続
		Connection connection = createDBConnection();
		PreparedStatement statement = null;
		ResultSet resultSet = null;
		if (connection == null) {
			return "JJ901SQL00101.jsp";
		}
		connection.setAutoCommit(false);

		// 出力用一時ファイルの作成
		File tmpFile = null;
		tmpFile = makeTmpFile();

		try {
			// SQL実行
			statement = connection.prepareStatement(strSql);
			statement.setQueryTimeout(TIMEOUT_SEC);
			resultSet = statement.executeQuery();

			// 一時ファイルへのデータ出力
			if ("tsv".equals(form.downloadExtension) || "csv".equals(form.downloadExtension)) {
				writeTsvCsvFile(tmpFile, resultSet);
			} else {
				writeExcelFile(tmpFile, resultSet);
			}

		} catch (Exception e) {
			dispMessage = e.getMessage();

			// エラー時はごみなるため、一時ファイルを削除
			FileUtils.forceDelete(tmpFile);
			return "JJ901SQL00101.jsp";

		} finally {
			// UPDATE,INSERTを許さない機能のため強制ロールバックを行う
			connection.rollback();

			ResultSetUtil.close(resultSet);
			StatementUtil.close(statement);
			ConnectionUtil.close(connection);
		}

		try {
			// ファイルダウンロード
			streamOutFile(tmpFile);
		} catch (Exception e) {
			dispMessage = e.getMessage();
			return "JJ901SQL00101.jsp";

		} finally {
			// 出力用一時ファイルの削除
			FileUtils.forceDelete(tmpFile);
		}

		return null;
	}

	/**
	 * 一時ファイル作成
	 *
	 * @return
	 * @throws Exception
	 */
	private File makeTmpFile() throws Exception {

		// 他のユーザと被らないよう、システム日時（ミリ秒）含めてのファイル名を設定
		String outputFile;
		SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyyMMddHHmmssSSS");
		String strCurrentTime = DATE_FORMAT.format(r2Date.get());
		if ("tsv".equals(form.downloadExtension)) {
			outputFile = strCurrentTime + ".tsv";
		} else if ("csv".equals(form.downloadExtension)) {
			outputFile = strCurrentTime + ".csv";
		} else {
			outputFile = strCurrentTime + ".xlsx";
		}

		// 一時ファイル用のディレクトリ作成
		File OUTPUT_DIR = new File(EnvValueDefineUtil.getValue("SQLTOOL1_TMPFILE_OUTPUT_DIR"));
		FileUtils.forceMkdir(OUTPUT_DIR);

		return new File(OUTPUT_DIR.getPath() + File.separator + outputFile);
	}

	/**
	 * 一時ファイルへデータ出力（TSV、CSV）
	 *
	 * @return
	 * @throws Exception
	 */
	private void writeTsvCsvFile(File outputFile, ResultSet resultSet) throws Exception {

		// SQL結果カラム名格納
		List<String> outputColumnName = new ArrayList<String>();
		List<Integer> columnType = new ArrayList<Integer>();
		columnType.add(0); // カラム数と合わせるために、空カラム追加
		ResultSetMetaData rsmd = resultSet.getMetaData();
		for (int i = 1; i <= rsmd.getColumnCount(); i++) {
			outputColumnName.add(rsmd.getColumnName(i));
			columnType.add(rsmd.getColumnType(i));
		}

		R2CsvListWriter writer;
		if ("tsv".equals(form.downloadExtension)) {
			writer = fileManager
					.createTsvFileWriter()
					.setOutputFilePath(outputFile.getAbsolutePath())
					.setSkipEscape(true)
					.setNewline("\r\n")
					.setOutputEncodingType(form.charSet)
					.setOutputHeader(outputColumnName.toArray(new String[outputColumnName.size()]))
					.getWriter();
		} else {
			writer = fileManager
					.createCsvFileWriter()
					.setOutputFilePath(outputFile.getAbsolutePath())
					.setSkipEscape(true)
					.setNewline("\r\n")
					.setOutputEncodingType(form.charSet)
					.setOutputHeader(outputColumnName.toArray(new String[outputColumnName.size()]))
					.getWriter();
		}

		try {
			// SQL結果レコード格納
			List<String> record;
			while (resultSet.next()) {
				record = new ArrayList<String>();
				for (int j = 1; j <= outputColumnName.size(); j++) {
					record.add(getResultValue(resultSet, columnType, j));
				}
				writer.write(record, "");
			}

		} catch (Exception e) {
			throw e;

		} finally {
			writer.close();
		}
	}

	/**
	 * 一時ファイルへデータ出力（Excel）
	 *
	 * @return
	 * @throws Exception
	 */
	private void writeExcelFile(File outputFile, ResultSet resultSet) throws Exception {

		// Excel book作成（メモリ圧迫対策のためSXSSF形式）
		SXSSFWorkbook book = new SXSSFWorkbook();
		FileOutputStream fos = new FileOutputStream(outputFile);

		try {
			// SQL結果カラム名格納
			List<String> outputColumnName = new ArrayList<String>();
			List<Integer> columnType = new ArrayList<Integer>();
			columnType.add(0); // カラム数と合わせるために、空カラム追加
			ResultSetMetaData rsmd = resultSet.getMetaData();
			for (int i = 1; i <= rsmd.getColumnCount(); i++) {
				outputColumnName.add(rsmd.getColumnName(i));
				columnType.add(rsmd.getColumnType(i));
			}

			// カラム名の出力
			Sheet sheet = book.createSheet();
			Row row = sheet.createRow(0);
			Cell cell;
			for (int cellCnt = 0; cellCnt < outputColumnName.size(); cellCnt++) {
				cell = row.createCell(cellCnt);
				cell.setCellType(Cell.CELL_TYPE_STRING);
				cell.setCellValue(new XSSFRichTextString(outputColumnName.get(cellCnt)));
			}

			// SQL結果レコード格納
			for (int rowCnt = 1; resultSet.next(); rowCnt++) {
				row = sheet.createRow(rowCnt);

				for (int cellCnt = 0; cellCnt < outputColumnName.size(); cellCnt++) {
					cell = row.createCell(cellCnt);
					cell.setCellValue(new XSSFRichTextString(getResultValue(resultSet, columnType, cellCnt + 1)));
				}
			}
			book.write(fos);

		} catch (Exception e) {
			throw e;

		} finally {
			IOUtils.closeQuietly(fos);
			book.dispose();
		}
	}

	/**
	 * レスポンスオブジェクトへSELECT結果ファイルをストリーム
	 *
	 * @param fileOut
	 * @throws Exception
	 */
	private void streamOutFile(File fileOut) throws Exception {
		HttpServletResponse res = ResponseUtil.getResponse();
		OutputStream os = res.getOutputStream();
		FileInputStream hFile = new FileInputStream(fileOut);
		BufferedInputStream bis = new BufferedInputStream(hFile);

		// レスポンス設定
		res.setContentType("application/octet-stream");
		res.setHeader("Content-Disposition", "filename=\"" + fileOut.getName() + "\"");

		// ファイル読み込み　＆　ストリーム書き出し
		try {
			int len = 0;
			byte[] buffer = new byte[2048];
			while ((len = bis.read(buffer)) >= 0) {
				os.write(buffer, 0, len);
			}

		} catch (Exception e) {
			throw e;

		} finally {
			IOUtils.closeQuietly(bis);
			IOUtils.closeQuietly(hFile);
			IOUtils.closeQuietly(os);
		}
	}

	/**
	 * 更新処理(※要検証コード)
	 *
	 * @return
	 */
	@Execute(validator = false)
	public String update() throws Exception {

		// 検証コードチェック
		String CHECK_KEY = "bab2b9cb6b20f27a5e9e63629c25ebc2";
		String keyTemp = jjmd5.encrypto(form.key);
		if (!CHECK_KEY.equals(keyTemp)) {
			dispMessage = "検証コードが不正です。";
			return "JJ901SQL00101.jsp";
		}

		// SQL文のセミコロン除去
		String strSql = removeLastSemicolon(form.sql);

		// ＤＢ接続
		Connection connection = createDBConnection();
		PreparedStatement statement = null;
		ResultSet resultSet = null;
		if (connection == null) {
			return "JJ901SQL00101.jsp";
		}

		try {
			int updateCount = updateExcute(connection, strSql);

			if (updateCount == 0) {
				dispMessage = "更新対象が存在しません";
			}
			dispMessage = updateCount + "件を更新しました";

		} catch (Exception e) {
			dispMessage = e.getMessage();

		} finally {
			ResultSetUtil.close(resultSet);
			StatementUtil.close(statement);
			ConnectionUtil.close(connection);
		}

		return "JJ901SQL00101.jsp";
	}

	/**
	 * DB更新実行
	 *
	 * @param connection
	 * @param sql
	 * @throws Exception
	 */
	private int updateExcute(Connection connection, String sql) throws Exception {

		PreparedStatement statement = null;
		ResultSet resultSet = null;

		try {
			statement = connection.prepareStatement(sql);
			statement.setQueryTimeout(TIMEOUT_SEC);
			int updateCount = statement.executeUpdate();

			return updateCount;

		} catch (Exception e) {
			throw e;

		} finally {
			ResultSetUtil.close(resultSet);
			StatementUtil.close(statement);
		}

	}
}
