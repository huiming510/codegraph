package jp.co.rct.jj.action;

import java.util.ArrayList;
import java.util.List;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;

import org.apache.log4j.Logger;
import org.seasar.struts.annotation.Execute;

import jp.co.rct.jj.base.env.EnvValueDefineUtil;
import r2framework.abtest.entity.AbTest;
import r2framework.abtest.entity.AbTestCase;
import r2framework.abtest.entity.Site;
import r2framework.abtest.util.YamlUtil;
import r2framework.core.util.R2Date;

public class JJ901ABTEST002Action {

	@Resource
	protected R2Date r2Date;

	/** リクエスト */
	@Resource
	private HttpServletRequest request;

	/** Log4J Logger */
	private static final Logger logger = Logger.getLogger(JJ901ABTEST002Action.class);

	// 賃貸用ABテストyamlファイルのパス
	private static final String FR_ABTEST_YAML_PATH = EnvValueDefineUtil.getValue("FR_ABTEST_YAML_PATH")
			.concat("/xjj-ol-front-fr.yaml");

	public long fileDate = 0;
	public String executeMessage = "";
	public List<AbTestId> abTestIdList = new ArrayList<AbTestId>();
	public String envName;

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
		logger.info("ABテスト切り替えツール表示 利用ユーザID:" + request.getRemoteUser());

		//画面表示用に各検品の名称を取得
		envName = EnvValueDefineUtil.getValue("KENPIN_NAME");

		//yamlファイルの中身を画面表示用に取得
		Site site = YamlUtil.load(FR_ABTEST_YAML_PATH, Site.class);
		abTestIdList = makeDispData(site);
		logger.info(fileDate);
		return "JJ901ABTEST00201.jsp";
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

}
