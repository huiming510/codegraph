package jp.co.rct.jj.action;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.List;

import javax.annotation.Resource;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.seasar.framework.beans.util.BeanMap;
import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;

import jp.co.rct.jj.form.JJ901FILE001Form;

public class JJ901FILE001Action {

	@ActionForm
	@Resource(name = "JJ901FILE001Form")
	private JJ901FILE001Form form;

	public File[] files;

	//ファイルList
	public List<BeanMap> fileList = new ArrayList<BeanMap>();

	//ディレクトリList
	public List<BeanMap> dirList = new ArrayList<BeanMap>();

	private SimpleDateFormat df = new SimpleDateFormat("yyyy/MM/dd HH:mm:ss");

	/** _response */
	public HttpServletResponse response;

	public HttpServletRequest request;

	@Execute(validator = false)
	public String index() {

		if (form.strPath == null || "".equals(form.strPath)) {
			form.strPath = "/";
		}

		files = dirpath(form.strPath);
		if (files == null) {
			files = filepath(form.strPath);
		}

		if (files == null) {
			form.strErr = "指定したディレクトリは存在しません";
		} else if (files.length == 0) {
			form.strErr = "指定したディレクトリは存在しますが、空です";
		} else {
			for (int i = 0; i < files.length; i++) {
				BeanMap map = new BeanMap();

				if (files[i].isDirectory()) {
					map.put("fileName", files[i].getName());
					map.put("fileSize", "<DIR>");
					map.put("fileModify", df.format(files[i].lastModified()));
					map.put("filePath", files[i].getAbsolutePath());
					dirList.add(map);
				} else {
					map.put("fileName", files[i].getName());
					map.put("fileSize", Math.ceil(files[i].length() / 1024 + 1) + "KB");
					map.put("fileModify", df.format(files[i].lastModified()));
					map.put("filePath", files[i].getAbsolutePath());
					fileList.add(map);
				}
			}
		}

		return "JJ901FILE00101.jsp";
	}

	@Execute(validator = false)
	public String download() {
		File file;
		try {
			file = new File(form.strPath);
			printOutFile(request, response, file);
			return null;

		} catch (Exception ex) {
			form.strErr = ex.getMessage();
		}

		return "JJ901FILE00101.jsp";
	}

	/**
	 * ディレクトリパスから配下のファイルやディレクトリを返す
	 *
	 * @param dpath
	 * @return
	 */
	private File[] dirpath(String dpath) {
		File dirpath = new File(dpath);
		File[] files = dirpath.listFiles();
		return files;
	}

	/**
	 * ファイルパスから該当するファイルを配列形式で返す
	 *
	 * @param fpath
	 * @return
	 */
	private File[] filepath(String fpath) {
		File filepath = new File(fpath);
		File[] files = null;
		if (filepath.exists()) {
			files = new File[] { filepath };
		}
		return files;
	}

	private void printOutFile(HttpServletRequest req, HttpServletResponse res, File fileOut)
			throws ServletException, IOException {
		OutputStream os = res.getOutputStream();
		try {
			FileInputStream hFile = new FileInputStream(fileOut);
			BufferedInputStream bis = new BufferedInputStream(hFile);

			//レスポンス設定
			res.setContentType("application/octet-stream");
			res.setHeader("Content-Disposition", "filename=\"" + fileOut.getName() + "\"");

			int len = 0;
			byte[] buffer = new byte[1024];
			while ((len = bis.read(buffer)) >= 0) {
				os.write(buffer, 0, len);
			}

			bis.close();
		} catch (IOException e) {
			form.strErr = e.getMessage();
		} finally {

			if (os != null) {
				try {
					os.close();
				} catch (IOException e) {

				} finally {
					os = null;
				}
			}
		}
	}
}
