package jp.co.rct.jj.action;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.List;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;

import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;
import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;

import com.opensymphony.oscache.util.StringUtil;

import jp.co.rct.jj.base.env.EnvValueDefineUtil;
import jp.co.rct.jj.form.JJ901ABTEST001Form;
import r2framework.abtest.entity.AbTest;
import r2framework.abtest.entity.AbTestCase;
import r2framework.abtest.entity.Site;
import r2framework.abtest.util.YamlUtil;
import r2framework.core.util.R2Date;

public class JJ901ABTEST001Action {

	/** アクションフォーム */
	@ActionForm
	@Resource(name = "JJ901ABTEST001Form")
	private JJ901ABTEST001Form abtestform;

	@Resource
	protected R2Date r2Date;

	/** リクエスト */
	@Resource
	private HttpServletRequest request;

	/** Log4J Logger */
	private static final Logger logger = Logger.getLogger(JJ901ABTEST001Action.class);

	private static final SimpleDateFormat formatter = new SimpleDateFormat("yyyyMMddHHmmss");

	// 賃貸用ABテストyamlファイルのパス
	private static final String FR_ABTEST_YAML_PATH = EnvValueDefineUtil.getValue("FR_ABTEST_YAML_PATH").concat("/xjj-ol-front-fr.yaml");
	private static final String NUMERIC_ERROR_MSG = "数字で入力してください";
	private static final String RATIO_SUM_ERROR_MSG = "比率の合計は100にしてください";
	private static final String YAML_DATE_ERROR_MSG = "Yamlファイルが更新されていたため処理中止しました";
	private static final String SAME_ID_ERROR_MSG = "同じテストIDが既に存在します";

	public String fileDate = "0";
	public String executeMessage = "";
	public List<AbTestId> abTestIdList = new ArrayList<AbTestId>();
	public String envName = EnvValueDefineUtil.getValue("KENPIN_NAME");;

	public class AbTestId {
		public String testId;
		public String version;
		public List<TestCase> caseList;
	}

	public class TestCase {
		public String patternId;
		public String ratio;
	}

	/**
	 * 初期表示
	 */
	@Execute(validator = false)
	public String index() {

		//yamlファイルの中身を画面表示用に取得
		Site site = YamlUtil.load(FR_ABTEST_YAML_PATH, Site.class);
		abTestIdList = makeDispData(site);
		File yamlFile = new File(FR_ABTEST_YAML_PATH);
		fileDate = String.valueOf(yamlFile.lastModified());
		logger.info(fileDate);
		return "JJ901ABTEST00101.jsp";
	}

	/**
	 * テスト比率更新
	 *
	 * @return
	 */
	@Execute(validator = false)
	public String update() throws Exception {

		//数値チェック
		if (!isNumericParam()) {
			executeMessage = NUMERIC_ERROR_MSG;
			return "JJ901ABTEST00101.jsp";
		}

		//比率の合計
		int ratioSum = Integer.parseInt(abtestform.ratio0) + Integer.parseInt(abtestform.ratio1)
				+ Integer.parseInt(abtestform.ratio2) + Integer.parseInt(abtestform.ratio3)
				+ Integer.parseInt(abtestform.ratio4);
		if (!isHundled(ratioSum)) {
			executeMessage = RATIO_SUM_ERROR_MSG;
			return "JJ901ABTEST00101.jsp";
		}

		//Yamlファイルの更新日付が画面を開いたときと異なる場合はエラー
		File yamlFile = new File(FR_ABTEST_YAML_PATH);
		if (!isSameDateYaml(abtestform.fileDate, String.valueOf(yamlFile.lastModified()))) {
			executeMessage = YAML_DATE_ERROR_MSG;
			return "JJ901ABTEST00101.jsp";
		}

		//バックアップを作成する、バックアップファイルは元のファイル名に日付を付与する（例:xjj-ol-front-fr.yaml20190814
		makeBackUpYaml(FR_ABTEST_YAML_PATH, FR_ABTEST_YAML_PATH.concat(formatter.format(r2Date.get())));

		//入力されている内容でyamlファイルを作成して上書き
		Site site = YamlUtil.load(FR_ABTEST_YAML_PATH, Site.class);
		YamlUtil.save(FR_ABTEST_YAML_PATH, updateRatio(site));

		//上書きしたyamlの中身を画面表示用に取得
		site = YamlUtil.load(FR_ABTEST_YAML_PATH, Site.class);
		abTestIdList = makeDispData(site);
		File newYamlFile = new File(FR_ABTEST_YAML_PATH);
		fileDate = String.valueOf(newYamlFile.lastModified());

		//POSTで送られたテストIDの値を取得
		String testId = (String) request.getParameter("testId");

		//処理結果
		executeMessage = testId + "の更新完了";

		return "JJ901ABTEST00101.jsp";
	}

	/**
	 * テストID削除
	 *
	 * @return
	 * @throws Exception
	 */
	@Execute(validator = false)
	public String delete() throws Exception {

		//Yamlファイルの更新日付が画面を開いたときと異なる場合はエラー
		File yamlFile = new File(FR_ABTEST_YAML_PATH);
		if (!isSameDateYaml(abtestform.fileDate, String.valueOf(yamlFile.lastModified()))) {
			executeMessage = YAML_DATE_ERROR_MSG;
			return "JJ901ABTEST00101.jsp";
		}

		//バックアップを作成する、バックアップファイルは元のファイル名に日付を付与する（例:xjj-ol-front-fr.yaml20190814
		makeBackUpYaml(FR_ABTEST_YAML_PATH, FR_ABTEST_YAML_PATH.concat(formatter.format(r2Date.get())));

		//入力されている内容でyamlファイルを作成して上書き
		Site site = YamlUtil.load(FR_ABTEST_YAML_PATH, Site.class);
		YamlUtil.save(FR_ABTEST_YAML_PATH, deleteId(site));

		//上書きしたyamlの中身を画面表示用に取得
		site = YamlUtil.load(FR_ABTEST_YAML_PATH, Site.class);
		abTestIdList = makeDispData(site);
		File newYamlFile = new File(FR_ABTEST_YAML_PATH);
		fileDate = String.valueOf(newYamlFile.lastModified());

		//POSTで送られたテストIDの値を取得
		String testId = (String) request.getParameter("testId");

		//処理結果
		executeMessage = testId + "の削除完了";

		return "JJ901ABTEST00101.jsp";
	}

	/**
	 * テストID追加
	 *
	 * @return
	 * @throws Exception
	 */
	@Execute(validator = false)
	public String add() throws Exception {

		//数値チェック
		if (!isNumericParam()) {
			executeMessage = NUMERIC_ERROR_MSG;
			return "JJ901ABTEST00101.jsp";
		}

		//比率の合計
		int ratioSum = Integer.parseInt(abtestform.ratio0) + Integer.parseInt(abtestform.ratio1)
				+ Integer.parseInt(abtestform.ratio2) + Integer.parseInt(abtestform.ratio3)
				+ Integer.parseInt(abtestform.ratio4);
		if (!isHundled(ratioSum)) {
			executeMessage = RATIO_SUM_ERROR_MSG;
			return "JJ901ABTEST00101.jsp";
		}

		//Yamlファイルの更新日付が画面を開いたときと異なる場合はエラー
		File yamlFile = new File(FR_ABTEST_YAML_PATH);
		if (!isSameDateYaml(abtestform.fileDate, String.valueOf(yamlFile.lastModified()))) {
			executeMessage = YAML_DATE_ERROR_MSG;
			return "JJ901ABTEST00101.jsp";
		}

		//バックアップを作成する、バックアップファイルは元のファイル名に日付を付与する（例:xjj-ol-front-fr.yaml20190814
		makeBackUpYaml(FR_ABTEST_YAML_PATH, FR_ABTEST_YAML_PATH.concat(formatter.format(r2Date.get())));

		//新規テストIDを追加したyamlを生成、既存のIDが指定された場合はエラー
		Site site = YamlUtil.load(FR_ABTEST_YAML_PATH, Site.class);
		try {
			YamlUtil.save(FR_ABTEST_YAML_PATH, addId(site));
		} catch (Exception e) {
			logger.error(SAME_ID_ERROR_MSG);
			executeMessage = SAME_ID_ERROR_MSG;
			return "JJ901ABTEST00101.jsp";
		}

		//上書きしたyamlの中身を画面表示用に取得
		site = YamlUtil.load(FR_ABTEST_YAML_PATH, Site.class);
		abTestIdList = makeDispData(site);
		File newYamlFile = new File(FR_ABTEST_YAML_PATH);
		fileDate = String.valueOf(newYamlFile.lastModified());

		//POSTで送られたテストIDの値を取得
		String testId = (String) request.getParameter("testId");

		//処理結果
		executeMessage = testId + "の追加完了";

		return "JJ901ABTEST00101.jsp";
	}

	/**
	 * 現在のyamlファイルから表示用データを作成する
	 *
	 * @param site 現在配置されているyamlファイルから取得した値
	 * @return 画面表示用データ
	 */
	private List<AbTestId> makeDispData(Site site) {

		List<AbTestId> abTestIdList = new ArrayList<AbTestId>();

		for (AbTest abtest : site.tests) {
			AbTestId abTestId = new AbTestId();
			List<TestCase> caseList = new ArrayList<TestCase>();

			abTestId.testId = abtest.getTestId();
			abTestId.version = String.valueOf(abtest.getVersion());

			for (AbTestCase abtestcase : abtest.cases) {
				TestCase testCase = new TestCase();
				testCase.patternId = abtestcase.getPatternId();
				testCase.ratio = String.valueOf(abtestcase.getRatio());
				caseList.add(testCase);
			}

			abTestId.caseList = caseList;
			abTestIdList.add(abTestId);
		}
		return abTestIdList;
	}

	/**
	 * パラメータチェック
	 */
	private Boolean isNumericParam() {

		//数字チェック
		if (!StringUtils.isNumeric(abtestform.version))
			return false;
		if (!StringUtils.isNumeric(abtestform.ratio0))
			return false;
		if (!StringUtils.isNumeric(abtestform.ratio1))
			return false;
		if (!StringUtils.isNumeric(abtestform.ratio2))
			return false;
		if (!StringUtils.isNumeric(abtestform.ratio3))
			return false;
		if (!StringUtils.isNumeric(abtestform.ratio4))
			return false;

		return true;
	}

	/**
	 * 渡された数値が100か確認する
	 *
	 * @param ratioSum 比率の合計
	 * @return true:渡された数値は100 false:渡された数値は100でない
	 */
	private Boolean isHundled(int ratioSum) {
		//比率合計チェック
		if (ratioSum != 100)
			return false;

		return true;
	}

	/**
	 * ファイル更新日付が画面を開いた時と同じか確認する
	 *
	 * @param beforeDate 画面を開いた時のyamlの更新時間
	 * @param nowDate 現在のyamlの更新時間
	 * @return true:同じ false:異なっている
	 */
	private Boolean isSameDateYaml(String beforeDate, String nowDate) {
		if (beforeDate.equals(nowDate))
			return true;
		return false;
	}

	/**
	 * 指定されたファイルをバックアップする
	 *
	 * @param frAbtestYamlPath バックアップ元のファイルパス
	 * @param backupName バックアップファイルのパス
	 * @return
	 * @throws IOException
	 */
	private String makeBackUpYaml(String frAbtestYamlPath, String backupFilePath) throws IOException {

		File srcFile = new File(frAbtestYamlPath);
		File backupFile = new File(backupFilePath);

		InputStream input = new FileInputStream(srcFile);
		OutputStream output = new FileOutputStream(backupFile);

		int DEFAULT_BUFFER_SIZE = 1024 * 4;
		byte[] buffer = new byte[DEFAULT_BUFFER_SIZE];
		int size = -1;
		while (-1 != (size = input.read(buffer))) {
			output.write(buffer, 0, size);
		}
		input.close();
		output.close();

		return null;
	}

	/**
	 * 画面で入力された内容で比率を更新する。
	 *
	 * @param site 現在配置されているYamlから取得した定義
	 */
	private Site updateRatio(Site site) {

		int i = 0;
		for (AbTest abtest : site.tests) {
			if (abtest.getTestId().equals(abtestform.testId)) {
				abtest.setVersion(Integer.parseInt(abtestform.version));
				int j = 0;
				for (AbTestCase abtestcase : abtest.cases) {
					if (abtestcase.getPatternId().equals(abtestform.patternId0)) {
						abtestcase.setRatio(Integer.parseInt(abtestform.ratio0));
						abtest.cases.set(j, abtestcase);
					}
					if (abtestcase.getPatternId().equals(abtestform.patternId1)) {
						abtestcase.setRatio(Integer.parseInt(abtestform.ratio1));
						abtest.cases.set(j, abtestcase);
					}
					if (abtestcase.getPatternId().equals(abtestform.patternId2)) {
						abtestcase.setRatio(Integer.parseInt(abtestform.ratio2));
						abtest.cases.set(j, abtestcase);
					}
					if (abtestcase.getPatternId().equals(abtestform.patternId3)) {
						abtestcase.setRatio(Integer.parseInt(abtestform.ratio3));
						abtest.cases.set(j, abtestcase);
					}
					if (abtestcase.getPatternId().equals(abtestform.patternId4)) {
						abtestcase.setRatio(Integer.parseInt(abtestform.ratio4));
						abtest.cases.set(j, abtestcase);
					}
					j++;
				}
				site.tests.set(i, abtest);
			}
			i++;
		}
		return site;
	}

	/**
	 * 画面で指定された削除対象を削除する。
	 *
	 * @param site 現在配置されているYamlから取得した定義
	 */
	private Site deleteId(Site site) {

		for (int i = 0; site.tests.size() > i; i++) {
			if (site.tests.get(i).getTestId().equals(abtestform.testId)) {
				site.tests.remove(i);
				break;
			}
		}
		return site;
	}

	/**
	 * 画面で入力された新規IDを追加する。
	 *
	 * @param site 現在配置されているYamlから取得した定義
	 * @throws Exception
	 */
	private Site addId(Site site) throws Exception {

		//Yamlファイルに同じIDが存在した場合処理を中止する
		for (int i = 0; site.tests.size() > i; i++) {
			if (site.tests.get(i).getTestId().equals(abtestform.testId)) {
				throw new Exception();
			}
		}

		AbTest addAbTest = new AbTest();
		List<AbTestCase> caseList = new ArrayList<AbTestCase>();

		//新規追加IDとバージョンを設定
		addAbTest.setTestId(abtestform.testId);
		addAbTest.setVersion(Integer.parseInt(abtestform.version));

		//パターンを設定
		for (int i = 0; 5 > i; i++) {
			AbTestCase addAbTestCase = new AbTestCase();
			switch (i) {
				case 0:
					if (!StringUtil.isEmpty(abtestform.patternId0)) {
						addAbTestCase.setPatternId(abtestform.patternId0);
						addAbTestCase.setRatio(Integer.parseInt(abtestform.ratio0));
						caseList.add(addAbTestCase);
					}
					break;

				case 1:
					if (!StringUtil.isEmpty(abtestform.patternId1)) {
						addAbTestCase.setPatternId(abtestform.patternId1);
						addAbTestCase.setRatio(Integer.parseInt(abtestform.ratio1));
						caseList.add(addAbTestCase);
					}
					break;

				case 2:
					if (!StringUtil.isEmpty(abtestform.patternId2)) {
						addAbTestCase.setPatternId(abtestform.patternId2);
						addAbTestCase.setRatio(Integer.parseInt(abtestform.ratio2));
						caseList.add(addAbTestCase);
					}
					break;

				case 3:
					if (!StringUtil.isEmpty(abtestform.patternId3)) {
						addAbTestCase.setPatternId(abtestform.patternId3);
						addAbTestCase.setRatio(Integer.parseInt(abtestform.ratio3));
						caseList.add(addAbTestCase);
					}
					break;

				case 4:
					if (!StringUtil.isEmpty(abtestform.patternId4)) {
						addAbTestCase.setPatternId(abtestform.patternId4);
						addAbTestCase.setRatio(Integer.parseInt(abtestform.ratio4));
						caseList.add(addAbTestCase);
					}
					break;
			}
		}
		addAbTest.cases = caseList;
		site.tests.add(addAbTest);

		return site;
	}
}
