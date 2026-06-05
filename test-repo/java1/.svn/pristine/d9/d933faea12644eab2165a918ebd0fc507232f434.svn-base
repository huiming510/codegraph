package jp.co.rct.jj.action;

import java.io.File;
import java.text.SimpleDateFormat;

import javax.annotation.Resource;

import org.apache.commons.lang.ObjectUtils;
import org.seasar.struts.annotation.Execute;

import jp.co.rct.jj.base.env.EnvValueDefineUtil;
import r2framework.core.helper.VirusCheckHelper;

public class JJ901SOPHOSCHECKAction {

	@Resource(name = "sophos")
	protected VirusCheckHelper helper;

	/** 表示スタイル */
	public String style;
	/** 対象ファイル保持ディレクトリ */
	public String checkDir;
	/** 対象ファイル数 */
	public String fileCnt;
	/** 開始時間 */
	public String startTime;
	/** 終了時間 */
	public String endTime;
	/** ウィルスなし */
	public String checkOffCnt;
	/** ウィルスあり */
	public String checkOnCnt;
	/** ウィルス不可 */
	public String checkCancelCnt;

	@Execute(validator = false)
	public String index() {

		// 対象ファイル保持ディレクトリ取得
		this.checkDir = EnvValueDefineUtil.getValue("SOPHOS_CHECK_FILE_PATH");

		// 対象ファイル件数取得
		File dirpath = new File(checkDir);
		File[] files = dirpath.listFiles();
		this.fileCnt = ObjectUtils.toString(files.length) + " ファイル";

		// 表示状態設定
		this.style = "display:none;";

		// 画面に戻る
		return "JJ901SOPHOSCHECK01.jsp";
	}

	@Execute(validator = false)
	public String check() {

		// 変数初期化
		int intCheckOffCnt = 0;
		int intCheckOnCnt = 0;
		int intCheckCancelCnt = 0;

		// 対象ファイル保持ディレクトリ取得
		this.checkDir = EnvValueDefineUtil.getValue("SOPHOS_CHECK_FILE_PATH");

		// 対象ファイル件数取得
		File dirpath = new File(checkDir);
		File[] files = dirpath.listFiles();
		this.fileCnt = ObjectUtils.toString(files.length) + " ファイル";

		// 開始時間取得
		SimpleDateFormat sdf = new SimpleDateFormat("yyyy/MM/dd HH:mm:ss.SSS");
		this.startTime = sdf.format(System.currentTimeMillis());

		// 対象ファイル保持ディレクトリにファイル有無判定
		if (files.length > 0) {
			for (int i = 0; i < files.length; i++) {
				try {
					// ウィルスチェック実施
					if (helper.check(files[i]) != 0) {
						// ウィルスあり
						intCheckOnCnt++;
					} else {
						// ウィルスなし
						intCheckOffCnt++;
					}
				} catch (Exception e) {
					// ウィルス不可
					intCheckCancelCnt++;
				}
			}
		}

		// 終了時間取得
		this.endTime = sdf.format(System.currentTimeMillis());

		// チェック結果設定
		this.checkOffCnt = ObjectUtils.toString(intCheckOffCnt) + " ファイル";
		this.checkOnCnt = ObjectUtils.toString(intCheckOnCnt) + " ファイル";
		this.checkCancelCnt = ObjectUtils.toString(intCheckCancelCnt) + " ファイル";

		// 表示状態設定
		this.style = "display:block;";

		// 画面に戻る
		return "JJ901SOPHOSCHECK01.jsp";
	}
}
