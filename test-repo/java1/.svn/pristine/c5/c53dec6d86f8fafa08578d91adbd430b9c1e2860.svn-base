package jp.co.rct.jj.action;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.zip.GZIPInputStream;

import javax.annotation.Resource;

import org.seasar.framework.util.StringUtil;
import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;

import jp.co.rct.jj.form.JJ901OPEN001Form;

public class JJ901OPEN001Action {

	@ActionForm
	@Resource(name = "JJ901OPEN001Form")
	private JJ901OPEN001Form form;

	public String fileContent;

	private static final long MAX_DISP_LINE = 3000;

	@Execute(validator = false)
	public String index() {

		String enCode = "UTF-8";

		if (form.cd == null || "".equals(form.cd)) {
			enCode = "UTF-8";
		} else if ("s".equals(form.cd) || "S".equals(form.cd)) {
			enCode = "SHIFT-JIS";
		} else if ("u".equals(form.cd) || "U".equals(form.cd)) {
			enCode = "UTF-8";
		}

		if (form.strPath == null || "".equals(form.strPath)) {
			form.strErr = "ファイル名がNULLです";
			return "JJ901OPEN00101.jsp";
		}

		File file = new File(form.strPath);

		if (!file.isFile() || !file.exists() || !file.canRead()) {
			form.strErr = "ファイルが読み取れません";
			return "JJ901OPEN00101.jsp";
		}

		if (StringUtil.isEmpty(form.line)) {
			form.line = String.valueOf(MAX_DISP_LINE);
		} else {
			try {
				if (Long.parseLong(form.line) > MAX_DISP_LINE) {
					form.line = String.valueOf(MAX_DISP_LINE);
				}
			} catch (NumberFormatException e) {
				form.strErr = "表示行数は数字で指定してください";
				return "JJ901OPEN00101.jsp";
			}
		}

		BufferedReader bufFileData = null;
		BufferedReader bufFileData2 = null;

		try {
			String line;

			StringBuffer sb = new StringBuffer();

			if (file.getName().endsWith(".gz")) {
				// 圧縮ファイル
				InputStreamReader inReader = new InputStreamReader(new GZIPInputStream(new FileInputStream(file)),
						enCode);
				bufFileData = new BufferedReader(inReader);

				InputStreamReader inReader2 = new InputStreamReader(new GZIPInputStream(new FileInputStream(file)),
						enCode);
				bufFileData2 = new BufferedReader(inReader2);
			} else {
				// 未圧縮ファイル
				InputStreamReader inReader = new InputStreamReader(new FileInputStream(file), enCode);
				bufFileData = new BufferedReader(inReader);

				InputStreamReader inReader2 = new InputStreamReader(new FileInputStream(file), enCode);
				bufFileData2 = new BufferedReader(inReader2);
			}

			long totalRow = 0;

			// 全行読み込みを行い行数を取得する
			while ((bufFileData.readLine()) != null) {
				totalRow++;
			}
			form.totalRow = String.valueOf(totalRow);

			// 行データを変数格納するのにも性能劣化があるので、行をスキップする処理と読み込む処理に分ける
			long skipRow = totalRow - Long.parseLong(form.line);
			if (skipRow <= 0) {
				skipRow = 0;
			}

			// スキップ処理
			for (int i = 0; i < skipRow; i++) {
				bufFileData2.readLine();
			}

			// 読み込み処理
			while ((line = bufFileData2.readLine()) != null) {
				sb.append(line + "\r\n");
			}

			fileContent = sb.toString();

		} catch (Exception e) {
			form.strErr = e.getMessage();
		} finally {
			if (bufFileData != null) {
				try {
					bufFileData.close();
				} catch (IOException e) {
				}
			}
			if (bufFileData2 != null) {
				try {
					bufFileData2.close();
				} catch (IOException e) {
				}
			}
		}

		return "JJ901OPEN00101.jsp";

	}

}
