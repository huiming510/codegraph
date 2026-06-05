package jp.co.rct.jj.action;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.io.Reader;
import java.net.Authenticator;
import java.net.HttpURLConnection;
import java.net.PasswordAuthentication;
import java.net.URL;
import java.net.URLEncoder;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletResponse;

import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;
import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;
import org.seasar.struts.exception.ActionMessagesException;

import jp.co.rct.jj.base.exception.JJSystemException;
import jp.co.rct.jj.form.JJ901SOLR001Form;

public class JJ901SOLR001Action {
	/** アクションフォーム */
	@ActionForm
	@Resource(name = "JJ901SOLR001Form")
	private JJ901SOLR001Form form;

	/** Log4J Logger */
	private static final Logger logger = Logger.getLogger(JJ901SOLR001Action.class);

	/** _response */
	public HttpServletResponse response;

	public PrintWriter out;

	private static final String es_1_seach_all_active = "http://172.21.241.89:9200/fr0001_dev001_active,fr0002_dev001_active,cm0001_fr_dev001_active/item/_qass/solr/";
	private static final String es_2_seach_all_active = "http://172.21.241.90:9200/fr0001_dev002_active,fr0002_dev002_active,cm0001_fr_dev002_active/item/_qass/solr/";
	private static final String es_3_seach_all_active = "http://172.21.241.91:9200/fr0001_dev003_active,fr0002_dev003_active,cm0001_fr_dev003_active/item/_qass/solr/";
	private static final String es_4_seach_all_active = "http://172.21.241.92:9200/fr0001_dev004_active,fr0002_dev004_active,cm0001_fr_dev004_active/item/_qass/solr/";
	private static final String es_5_seach_all_active = "http://172.21.241.92:9200/fr0001_dev005_active,fr0002_dev005_active,cm0001_fr_dev005_active/item/_qass/solr/";
	private static final String es_6_seach_all_active = "http://172.21.241.92:9200/fr0001_dev006_active,fr0002_dev006_active,cm0001_fr_dev006_active/item/_qass/solr/";
	private static final String es_7_seach_all_active = "http://172.21.241.93:9200/fr0001_dev007_active,fr0002_dev007_active,cm0001_fr_dev007_active/item/_qass/solr/";
	private static final String es_8_seach_all_active = "http://172.21.241.93:9200/fr0001_dev008_active,fr0002_dev008_active,cm0001_fr_dev008_active/item/_qass/solr/";
	private static final String es_9_seach_all_active = "http://172.21.241.93:9200/fr0001_dev009_active,fr0002_dev009_active,cm0001_fr_dev009_active/item/_qass/solr/";

	private static final String es_1_seach_fr_active = "http://172.21.241.89:9200/fr0001_dev001_active,fr0002_dev001_active/item/_qass/solr/";
	private static final String es_2_seach_fr_active = "http://172.21.241.90:9200/fr0001_dev002_active,fr0002_dev002_active/item/_qass/solr/";
	private static final String es_3_seach_fr_active = "http://172.21.241.91:9200/fr0001_dev003_active,fr0002_dev003_active/item/_qass/solr/";
	private static final String es_4_seach_fr_active = "http://172.21.241.92:9200/fr0001_dev004_active,fr0002_dev004_active/item/_qass/solr/";
	private static final String es_5_seach_fr_active = "http://172.21.241.92:9200/fr0001_dev005_active,fr0002_dev005_active/item/_qass/solr/";
	private static final String es_6_seach_fr_active = "http://172.21.241.92:9200/fr0001_dev006_active,fr0002_dev006_active/item/_qass/solr/";
	private static final String es_7_seach_fr_active = "http://172.21.241.93:9200/fr0001_dev007_active,fr0002_dev007_active/item/_qass/solr/";
	private static final String es_8_seach_fr_active = "http://172.21.241.93:9200/fr0001_dev008_active,fr0002_dev008_active/item/_qass/solr/";
	private static final String es_9_seach_fr_active = "http://172.21.241.93:9200/fr0001_dev009_active,fr0002_dev009_active/item/_qass/solr/";

	private static final String es_1_seach_fr0001_active = "http://172.21.241.89:9200/fr0001_dev001_active/item/_qass/solr/";
	private static final String es_2_seach_fr0001_active = "http://172.21.241.90:9200/fr0001_dev002_active/item/_qass/solr/";
	private static final String es_3_seach_fr0001_active = "http://172.21.241.91:9200/fr0001_dev003_active/item/_qass/solr/";
	private static final String es_4_seach_fr0001_active = "http://172.21.241.92:9200/fr0001_dev004_active/item/_qass/solr/";
	private static final String es_5_seach_fr0001_active = "http://172.21.241.92:9200/fr0001_dev005_active/item/_qass/solr/";
	private static final String es_6_seach_fr0001_active = "http://172.21.241.92:9200/fr0001_dev006_active/item/_qass/solr/";
	private static final String es_7_seach_fr0001_active = "http://172.21.241.93:9200/fr0001_dev007_active/item/_qass/solr/";
	private static final String es_8_seach_fr0001_active = "http://172.21.241.93:9200/fr0001_dev008_active/item/_qass/solr/";
	private static final String es_9_seach_fr0001_active = "http://172.21.241.93:9200/fr0001_dev009_active/item/_qass/solr/";

	private static final String es_1_seach_fr0002_active = "http://172.21.241.89:9200/fr0002_dev001_active/item/_qass/solr/";
	private static final String es_2_seach_fr0002_active = "http://172.21.241.90:9200/fr0002_dev002_active/item/_qass/solr/";
	private static final String es_3_seach_fr0002_active = "http://172.21.241.91:9200/fr0002_dev003_active/item/_qass/solr/";
	private static final String es_4_seach_fr0002_active = "http://172.21.241.92:9200/fr0002_dev004_active/item/_qass/solr/";
	private static final String es_5_seach_fr0002_active = "http://172.21.241.92:9200/fr0002_dev005_active/item/_qass/solr/";
	private static final String es_6_seach_fr0002_active = "http://172.21.241.92:9200/fr0002_dev006_active/item/_qass/solr/";
	private static final String es_7_seach_fr0002_active = "http://172.21.241.93:9200/fr0002_dev007_active/item/_qass/solr/";
	private static final String es_8_seach_fr0002_active = "http://172.21.241.93:9200/fr0002_dev008_active/item/_qass/solr/";
	private static final String es_9_seach_fr0002_active = "http://172.21.241.93:9200/fr0002_dev009_active/item/_qass/solr/";

	private static final String es_1_cm0001_active = "http://172.21.247.185:9200/cm0001_dev001_active/item/_qass/solr/";
	private static final String es_2_cm0001_active = "http://172.21.247.186:9200/cm0001_dev002_active/item/_qass/solr/";
	private static final String es_3_cm0001_active = "http://172.21.247.187:9200/cm0001_dev003_active/item/_qass/solr/";
	private static final String es_4_cm0001_active = "http://172.21.247.188:9200/cm0001_dev004_active/item/_qass/solr/";
	private static final String es_5_cm0001_active = "http://172.21.247.188:9200/cm0001_dev005_active/item/_qass/solr/";
	private static final String es_6_cm0001_active = "http://172.21.247.188:9200/cm0001_dev006_active/item/_qass/solr/";
	private static final String es_7_cm0001_active = "http://172.21.247.189:9200/cm0001_dev007_active/item/_qass/solr/";
	private static final String es_8_cm0001_active = "http://172.21.247.189:9200/cm0001_dev008_active/item/_qass/solr/";
	private static final String es_9_cm0001_active = "http://172.21.247.189:9200/cm0001_dev009_active/item/_qass/solr/";

	private static final String es_1_cm0002_active = "http://172.21.247.185:9200/cm0002_dev001_active/item/_qass/solr/";
	private static final String es_2_cm0002_active = "http://172.21.247.186:9200/cm0002_dev002_active/item/_qass/solr/";
	private static final String es_3_cm0002_active = "http://172.21.247.187:9200/cm0002_dev003_active/item/_qass/solr/";
	private static final String es_4_cm0002_active = "http://172.21.247.188:9200/cm0002_dev004_active/item/_qass/solr/";
	private static final String es_5_cm0002_active = "http://172.21.247.188:9200/cm0002_dev005_active/item/_qass/solr/";
	private static final String es_6_cm0002_active = "http://172.21.247.188:9200/cm0002_dev006_active/item/_qass/solr/";
	private static final String es_7_cm0002_active = "http://172.21.247.189:9200/cm0002_dev007_active/item/_qass/solr/";
	private static final String es_8_cm0002_active = "http://172.21.247.189:9200/cm0002_dev008_active/item/_qass/solr/";
	private static final String es_9_cm0002_active = "http://172.21.247.189:9200/cm0002_dev009_active/item/_qass/solr/";

	private static final String es_1_seach_all_standby = "http://172.21.241.89:9200/fr0001_dev001_standby,fr0002_dev001_standby,cm0001_fr_dev001_standby/item/_qass/solr/";
	private static final String es_2_seach_all_standby = "http://172.21.241.90:9200/fr0001_dev002_standby,fr0002_dev002_standby,cm0001_fr_dev002_standby/item/_qass/solr/";
	private static final String es_3_seach_all_standby = "http://172.21.241.91:9200/fr0001_dev003_standby,fr0002_dev003_standby,cm0001_fr_dev003_standby/item/_qass/solr/";
	private static final String es_4_seach_all_standby = "http://172.21.241.92:9200/fr0001_dev004_standby,fr0002_dev004_standby,cm0001_fr_dev004_standby/item/_qass/solr/";
	private static final String es_5_seach_all_standby = "http://172.21.241.92:9200/fr0001_dev005_standby,fr0002_dev005_standby,cm0001_fr_dev005_standby/item/_qass/solr/";
	private static final String es_6_seach_all_standby = "http://172.21.241.92:9200/fr0001_dev006_standby,fr0002_dev006_standby,cm0001_fr_dev006_standby/item/_qass/solr/";
	private static final String es_7_seach_all_standby = "http://172.21.241.93:9200/fr0001_dev007_standby,fr0002_dev007_standby,cm0001_fr_dev007_standby/item/_qass/solr/";
	private static final String es_8_seach_all_standby = "http://172.21.241.93:9200/fr0001_dev008_standby,fr0002_dev008_standby,cm0001_fr_dev008_standby/item/_qass/solr/";
	private static final String es_9_seach_all_standby = "http://172.21.241.93:9200/fr0001_dev009_standby,fr0002_dev009_standby,cm0001_fr_dev009_standby/item/_qass/solr/";

	private static final String es_1_seach_fr_standby = "http://172.21.241.89:9200/fr0001_dev001_standby,fr0002_dev001_standby/item/_qass/solr/";
	private static final String es_2_seach_fr_standby = "http://172.21.241.90:9200/fr0001_dev002_standby,fr0002_dev002_standby/item/_qass/solr/";
	private static final String es_3_seach_fr_standby = "http://172.21.241.91:9200/fr0001_dev003_standby,fr0002_dev003_standby/item/_qass/solr/";
	private static final String es_4_seach_fr_standby = "http://172.21.241.92:9200/fr0001_dev004_standby,fr0002_dev004_standby/item/_qass/solr/";
	private static final String es_5_seach_fr_standby = "http://172.21.241.92:9200/fr0001_dev005_standby,fr0002_dev005_standby/item/_qass/solr/";
	private static final String es_6_seach_fr_standby = "http://172.21.241.92:9200/fr0001_dev006_standby,fr0002_dev006_standby/item/_qass/solr/";
	private static final String es_7_seach_fr_standby = "http://172.21.241.93:9200/fr0001_dev007_standby,fr0002_dev007_standby/item/_qass/solr/";
	private static final String es_8_seach_fr_standby = "http://172.21.241.93:9200/fr0001_dev008_standby,fr0002_dev008_standby/item/_qass/solr/";
	private static final String es_9_seach_fr_standby = "http://172.21.241.93:9200/fr0001_dev009_standby,fr0002_dev009_standby/item/_qass/solr/";

	private static final String es_1_seach_fr0001_standby = "http://172.21.241.89:9200/fr0001_dev001_standby/item/_qass/solr/";
	private static final String es_2_seach_fr0001_standby = "http://172.21.241.90:9200/fr0001_dev002_standby/item/_qass/solr/";
	private static final String es_3_seach_fr0001_standby = "http://172.21.241.91:9200/fr0001_dev003_standby/item/_qass/solr/";
	private static final String es_4_seach_fr0001_standby = "http://172.21.241.92:9200/fr0001_dev004_standby/item/_qass/solr/";
	private static final String es_5_seach_fr0001_standby = "http://172.21.241.92:9200/fr0001_dev005_standby/item/_qass/solr/";
	private static final String es_6_seach_fr0001_standby = "http://172.21.241.92:9200/fr0001_dev006_standby/item/_qass/solr/";
	private static final String es_7_seach_fr0001_standby = "http://172.21.241.93:9200/fr0001_dev007_standby/item/_qass/solr/";
	private static final String es_8_seach_fr0001_standby = "http://172.21.241.93:9200/fr0001_dev008_standby/item/_qass/solr/";
	private static final String es_9_seach_fr0001_standby = "http://172.21.241.93:9200/fr0001_dev009_standby/item/_qass/solr/";

	private static final String es_1_seach_fr0002_standby = "http://172.21.241.89:9200/fr0002_dev001_standby/item/_qass/solr/";
	private static final String es_2_seach_fr0002_standby = "http://172.21.241.90:9200/fr0002_dev002_standby/item/_qass/solr/";
	private static final String es_3_seach_fr0002_standby = "http://172.21.241.91:9200/fr0002_dev003_standby/item/_qass/solr/";
	private static final String es_4_seach_fr0002_standby = "http://172.21.241.92:9200/fr0002_dev004_standby/item/_qass/solr/";
	private static final String es_5_seach_fr0002_standby = "http://172.21.241.92:9200/fr0002_dev005_standby/item/_qass/solr/";
	private static final String es_6_seach_fr0002_standby = "http://172.21.241.92:9200/fr0002_dev006_standby/item/_qass/solr/";
	private static final String es_7_seach_fr0002_standby = "http://172.21.241.93:9200/fr0002_dev007_standby/item/_qass/solr/";
	private static final String es_8_seach_fr0002_standby = "http://172.21.241.93:9200/fr0002_dev008_standby/item/_qass/solr/";
	private static final String es_9_seach_fr0002_standby = "http://172.21.241.93:9200/fr0002_dev009_standby/item/_qass/solr/";

	private static final String es_1_cm0001_standby = "http://172.21.247.185:9200/cm0001_dev001_standby/item/_qass/solr/";
	private static final String es_2_cm0001_standby = "http://172.21.247.186:9200/cm0001_dev002_standby/item/_qass/solr/";
	private static final String es_3_cm0001_standby = "http://172.21.247.187:9200/cm0001_dev003_standby/item/_qass/solr/";
	private static final String es_4_cm0001_standby = "http://172.21.247.188:9200/cm0001_dev004_standby/item/_qass/solr/";
	private static final String es_5_cm0001_standby = "http://172.21.247.188:9200/cm0001_dev005_standby/item/_qass/solr/";
	private static final String es_6_cm0001_standby = "http://172.21.247.188:9200/cm0001_dev006_standby/item/_qass/solr/";
	private static final String es_7_cm0001_standby = "http://172.21.247.189:9200/cm0001_dev007_standby/item/_qass/solr/";
	private static final String es_8_cm0001_standby = "http://172.21.247.189:9200/cm0001_dev008_standby/item/_qass/solr/";
	private static final String es_9_cm0001_standby = "http://172.21.247.189:9200/cm0001_dev009_standby/item/_qass/solr/";

	private static final String es_1_cm0002_standby = "http://172.21.247.185:9200/cm0002_dev001_standby/item/_qass/solr/";
	private static final String es_2_cm0002_standby = "http://172.21.247.186:9200/cm0002_dev002_standby/item/_qass/solr/";
	private static final String es_3_cm0002_standby = "http://172.21.247.187:9200/cm0002_dev003_standby/item/_qass/solr/";
	private static final String es_4_cm0002_standby = "http://172.21.247.188:9200/cm0002_dev004_standby/item/_qass/solr/";
	private static final String es_5_cm0002_standby = "http://172.21.247.188:9200/cm0002_dev005_standby/item/_qass/solr/";
	private static final String es_6_cm0002_standby = "http://172.21.247.188:9200/cm0002_dev006_standby/item/_qass/solr/";
	private static final String es_7_cm0002_standby = "http://172.21.247.189:9200/cm0002_dev007_standby/item/_qass/solr/";
	private static final String es_8_cm0002_standby = "http://172.21.247.189:9200/cm0002_dev008_standby/item/_qass/solr/";
	private static final String es_9_cm0002_standby = "http://172.21.247.189:9200/cm0002_dev009_standby/item/_qass/solr/";

	public String strResult = "";


	@Execute(validator = false)
	public String index() {
		String kenpin = form.side1;
		String index = form.side2;
		String status = form.side3;

		String side = kenpin + "_"+ index + "_" + status ;
		try
		{

			if (StringUtils.isEmpty(form.solrRequest)) {
				return "JJ901SOLR00101.jsp";
			} else if ("1".equals(form.solrRequest) && StringUtils.isEmpty(form.query)) {
				return "JJ901SOLR00101.jsp";
			} else if ("2".equals(form.solrRequest) && StringUtils.isEmpty(form.solrParam)) {
				return "JJ901SOLR00101.jsp";
			}

			StringBuilder strUrl = new StringBuilder();

			if ("es_1_seach_all_active".equals(side)) strUrl.append(es_1_seach_all_active);
			else if ("es_2_seach_all_active".equals(side)) strUrl.append(es_2_seach_all_active);
			else if ("es_3_seach_all_active".equals(side)) strUrl.append(es_3_seach_all_active);
			else if ("es_4_seach_all_active".equals(side)) strUrl.append(es_4_seach_all_active);
			else if ("es_5_seach_all_active".equals(side)) strUrl.append(es_5_seach_all_active);
			else if ("es_6_seach_all_active".equals(side)) strUrl.append(es_6_seach_all_active);
			else if ("es_7_seach_all_active".equals(side)) strUrl.append(es_7_seach_all_active);
			else if ("es_8_seach_all_active".equals(side)) strUrl.append(es_8_seach_all_active);
			else if ("es_9_seach_all_active".equals(side)) strUrl.append(es_9_seach_all_active);

			else if ("es_1_seach_fr_active".equals(side)) strUrl.append(es_1_seach_fr_active);
			else if ("es_2_seach_fr_active".equals(side)) strUrl.append(es_2_seach_fr_active);
			else if ("es_3_seach_fr_active".equals(side)) strUrl.append(es_3_seach_fr_active);
			else if ("es_4_seach_fr_active".equals(side)) strUrl.append(es_4_seach_fr_active);
			else if ("es_5_seach_fr_active".equals(side)) strUrl.append(es_5_seach_fr_active);
			else if ("es_6_seach_fr_active".equals(side)) strUrl.append(es_6_seach_fr_active);
			else if ("es_7_seach_fr_active".equals(side)) strUrl.append(es_7_seach_fr_active);
			else if ("es_8_seach_fr_active".equals(side)) strUrl.append(es_8_seach_fr_active);
			else if ("es_9_seach_fr_active".equals(side)) strUrl.append(es_9_seach_fr_active);

			else if ("es_1_seach_fr0001_active".equals(side)) strUrl.append(es_1_seach_fr0001_active);
			else if ("es_2_seach_fr0001_active".equals(side)) strUrl.append(es_2_seach_fr0001_active);
			else if ("es_3_seach_fr0001_active".equals(side)) strUrl.append(es_3_seach_fr0001_active);
			else if ("es_4_seach_fr0001_active".equals(side)) strUrl.append(es_4_seach_fr0001_active);
			else if ("es_5_seach_fr0001_active".equals(side)) strUrl.append(es_5_seach_fr0001_active);
			else if ("es_6_seach_fr0001_active".equals(side)) strUrl.append(es_6_seach_fr0001_active);
			else if ("es_7_seach_fr0001_active".equals(side)) strUrl.append(es_7_seach_fr0001_active);
			else if ("es_8_seach_fr0001_active".equals(side)) strUrl.append(es_8_seach_fr0001_active);
			else if ("es_9_seach_fr0001_active".equals(side)) strUrl.append(es_9_seach_fr0001_active);

			else if ("es_1_seach_fr0002_active".equals(side)) strUrl.append(es_1_seach_fr0002_active);
			else if ("es_2_seach_fr0002_active".equals(side)) strUrl.append(es_2_seach_fr0002_active);
			else if ("es_3_seach_fr0002_active".equals(side)) strUrl.append(es_3_seach_fr0002_active);
			else if ("es_4_seach_fr0002_active".equals(side)) strUrl.append(es_4_seach_fr0002_active);
			else if ("es_5_seach_fr0002_active".equals(side)) strUrl.append(es_5_seach_fr0002_active);
			else if ("es_6_seach_fr0002_active".equals(side)) strUrl.append(es_6_seach_fr0002_active);
			else if ("es_7_seach_fr0002_active".equals(side)) strUrl.append(es_7_seach_fr0002_active);
			else if ("es_8_seach_fr0002_active".equals(side)) strUrl.append(es_8_seach_fr0002_active);
			else if ("es_9_seach_fr0002_active".equals(side)) strUrl.append(es_9_seach_fr0002_active);

			else if ("es_1_cm0001_active".equals(side)) strUrl.append(es_1_cm0001_active);
			else if ("es_2_cm0001_active".equals(side)) strUrl.append(es_2_cm0001_active);
			else if ("es_3_cm0001_active".equals(side)) strUrl.append(es_3_cm0001_active);
			else if ("es_4_cm0001_active".equals(side)) strUrl.append(es_4_cm0001_active);
			else if ("es_5_cm0001_active".equals(side)) strUrl.append(es_5_cm0001_active);
			else if ("es_6_cm0001_active".equals(side)) strUrl.append(es_6_cm0001_active);
			else if ("es_7_cm0001_active".equals(side)) strUrl.append(es_7_cm0001_active);
			else if ("es_8_cm0001_active".equals(side)) strUrl.append(es_8_cm0001_active);
			else if ("es_9_cm0001_active".equals(side)) strUrl.append(es_9_cm0001_active);

			else if ("es_1_cm0002_active".equals(side)) strUrl.append(es_1_cm0002_active);
			else if ("es_2_cm0002_active".equals(side)) strUrl.append(es_2_cm0002_active);
			else if ("es_3_cm0002_active".equals(side)) strUrl.append(es_3_cm0002_active);
			else if ("es_4_cm0002_active".equals(side)) strUrl.append(es_4_cm0002_active);
			else if ("es_5_cm0002_active".equals(side)) strUrl.append(es_5_cm0002_active);
			else if ("es_6_cm0002_active".equals(side)) strUrl.append(es_6_cm0002_active);
			else if ("es_7_cm0002_active".equals(side)) strUrl.append(es_7_cm0002_active);
			else if ("es_8_cm0002_active".equals(side)) strUrl.append(es_8_cm0002_active);
			else if ("es_9_cm0002_active".equals(side)) strUrl.append(es_9_cm0002_active);

			else if ("es_1_seach_all_standby".equals(side)) strUrl.append(es_1_seach_all_standby);
			else if ("es_2_seach_all_standby".equals(side)) strUrl.append(es_2_seach_all_standby);
			else if ("es_3_seach_all_standby".equals(side)) strUrl.append(es_3_seach_all_standby);
			else if ("es_4_seach_all_standby".equals(side)) strUrl.append(es_4_seach_all_standby);
			else if ("es_5_seach_all_standby".equals(side)) strUrl.append(es_5_seach_all_standby);
			else if ("es_6_seach_all_standby".equals(side)) strUrl.append(es_6_seach_all_standby);
			else if ("es_7_seach_all_standby".equals(side)) strUrl.append(es_7_seach_all_standby);
			else if ("es_8_seach_all_standby".equals(side)) strUrl.append(es_8_seach_all_standby);
			else if ("es_9_seach_all_standby".equals(side)) strUrl.append(es_9_seach_all_standby);

			else if ("es_1_seach_fr_standby".equals(side)) strUrl.append(es_1_seach_fr_standby);
			else if ("es_2_seach_fr_standby".equals(side)) strUrl.append(es_2_seach_fr_standby);
			else if ("es_3_seach_fr_standby".equals(side)) strUrl.append(es_3_seach_fr_standby);
			else if ("es_4_seach_fr_standby".equals(side)) strUrl.append(es_4_seach_fr_standby);
			else if ("es_5_seach_fr_standby".equals(side)) strUrl.append(es_5_seach_fr_standby);
			else if ("es_6_seach_fr_standby".equals(side)) strUrl.append(es_6_seach_fr_standby);
			else if ("es_7_seach_fr_standby".equals(side)) strUrl.append(es_7_seach_fr_standby);
			else if ("es_8_seach_fr_standby".equals(side)) strUrl.append(es_8_seach_fr_standby);
			else if ("es_9_seach_fr_standby".equals(side)) strUrl.append(es_9_seach_fr_standby);

			else if ("es_1_seach_fr0001_standby".equals(side)) strUrl.append(es_1_seach_fr0001_standby);
			else if ("es_2_seach_fr0001_standby".equals(side)) strUrl.append(es_2_seach_fr0001_standby);
			else if ("es_3_seach_fr0001_standby".equals(side)) strUrl.append(es_3_seach_fr0001_standby);
			else if ("es_4_seach_fr0001_standby".equals(side)) strUrl.append(es_4_seach_fr0001_standby);
			else if ("es_5_seach_fr0001_standby".equals(side)) strUrl.append(es_5_seach_fr0001_standby);
			else if ("es_6_seach_fr0001_standby".equals(side)) strUrl.append(es_6_seach_fr0001_standby);
			else if ("es_7_seach_fr0001_standby".equals(side)) strUrl.append(es_7_seach_fr0001_standby);
			else if ("es_8_seach_fr0001_standby".equals(side)) strUrl.append(es_8_seach_fr0001_standby);
			else if ("es_9_seach_fr0001_standby".equals(side)) strUrl.append(es_9_seach_fr0001_standby);

			else if ("es_1_seach_fr0002_standby".equals(side)) strUrl.append(es_1_seach_fr0002_standby);
			else if ("es_2_seach_fr0002_standby".equals(side)) strUrl.append(es_2_seach_fr0002_standby);
			else if ("es_3_seach_fr0002_standby".equals(side)) strUrl.append(es_3_seach_fr0002_standby);
			else if ("es_4_seach_fr0002_standby".equals(side)) strUrl.append(es_4_seach_fr0002_standby);
			else if ("es_5_seach_fr0002_standby".equals(side)) strUrl.append(es_5_seach_fr0002_standby);
			else if ("es_6_seach_fr0002_standby".equals(side)) strUrl.append(es_6_seach_fr0002_standby);
			else if ("es_7_seach_fr0002_standby".equals(side)) strUrl.append(es_7_seach_fr0002_standby);
			else if ("es_8_seach_fr0002_standby".equals(side)) strUrl.append(es_8_seach_fr0002_standby);
			else if ("es_9_seach_fr0002_standby".equals(side)) strUrl.append(es_9_seach_fr0002_standby);

			else if ("es_1_cm0001_standby".equals(side)) strUrl.append(es_1_cm0001_standby);
			else if ("es_2_cm0001_standby".equals(side)) strUrl.append(es_2_cm0001_standby);
			else if ("es_3_cm0001_standby".equals(side)) strUrl.append(es_3_cm0001_standby);
			else if ("es_4_cm0001_standby".equals(side)) strUrl.append(es_4_cm0001_standby);
			else if ("es_5_cm0001_standby".equals(side)) strUrl.append(es_5_cm0001_standby);
			else if ("es_6_cm0001_standby".equals(side)) strUrl.append(es_6_cm0001_standby);
			else if ("es_7_cm0001_standby".equals(side)) strUrl.append(es_7_cm0001_standby);
			else if ("es_8_cm0001_standby".equals(side)) strUrl.append(es_8_cm0001_standby);
			else if ("es_9_cm0001_standby".equals(side)) strUrl.append(es_9_cm0001_standby);

			else if ("es_1_cm0002_standby".equals(side)) strUrl.append(es_1_cm0002_standby);
			else if ("es_2_cm0002_standby".equals(side)) strUrl.append(es_2_cm0002_standby);
			else if ("es_3_cm0002_standby".equals(side)) strUrl.append(es_3_cm0002_standby);
			else if ("es_4_cm0002_standby".equals(side)) strUrl.append(es_4_cm0002_standby);
			else if ("es_5_cm0002_standby".equals(side)) strUrl.append(es_5_cm0002_standby);
			else if ("es_6_cm0002_standby".equals(side)) strUrl.append(es_6_cm0002_standby);
			else if ("es_7_cm0002_standby".equals(side)) strUrl.append(es_7_cm0002_standby);
			else if ("es_8_cm0002_standby".equals(side)) strUrl.append(es_8_cm0002_standby);
			else if ("es_9_cm0002_standby".equals(side)) strUrl.append(es_9_cm0002_standby);

			else {
				return "JJ901SOLR00101.jsp";
			}

			response.setContentType("text/plain; charset=UTF-8");
			out = response.getWriter();

			if ("2".equals(form.solrRequest)) {
				strUrl.append("select/?");
				strUrl.append(form.solrParam.trim());
				strUrl.append("&version=2.2&indent=true");
			} else {
				strUrl.append("select/?q=");
				strUrl.append(URLEncoder.encode(form.query,"utf-8"));

				if (StringUtils.isNotEmpty(form.sort.trim())) {
					strUrl.append("&sort=");
					strUrl.append(URLEncoder.encode(form.sort.trim(),"utf-8"));
				}

				if (StringUtils.isNotEmpty(form.facetField.trim())) {
					strUrl.append("&facet=true&facet.field=");
					strUrl.append(URLEncoder.encode(form.facetField.trim(),"utf-8"));
					strUrl.append("&facet.offset=0&facet.limit=-1&facet.sort=true&facet.zeros=false&facet.missing=false");
				}

				if (StringUtils.isNotEmpty(form.groupField.trim())) {
					strUrl.append("&group=true&group.ngroups=true&group.field=");
					strUrl.append(URLEncoder.encode(form.groupField.trim(),"utf-8"));
					strUrl.append("&group.limit=5000&group.offset=0&group.facet=false&group.truncate=false&group.cache.percent=20");
				}

				if (StringUtils.isNotEmpty(form.field.trim())) {
					strUrl.append("&fl=");
					strUrl.append(form.field.trim());
				}

				if (StringUtils.isNotEmpty(form.start)) {
					strUrl.append("&start=");
					strUrl.append(form.start);
				} else {
					strUrl.append("&start=0");
				}

				if (StringUtils.isNotEmpty(form.rows)) {
					strUrl.append("&rows=");
					strUrl.append(form.rows);
				} else {
					strUrl.append("&rows=10");
				}

				response.setContentType("text/xml; charset=UTF-8");
				strUrl.append("&wt=xml");

				strUrl.append("&version=2.2&indent=true");
			}

			logger.info(strUrl.toString());

			URL url = new URL(strUrl.toString());
			HttpURLConnection urlconn = (HttpURLConnection)url.openConnection();

			urlconn.setConnectTimeout(10000);
			urlconn.setDoOutput(true);
			urlconn.setRequestMethod("GET");
			urlconn.setInstanceFollowRedirects(false);

			StringBuffer temp=new StringBuffer();
			InputStream in = new BufferedInputStream(urlconn.getInputStream());
			Reader rd=new InputStreamReader(in,"UTF-8");
			int c=0;
			while((c = rd.read()) != -1)
			{
				temp.append((char) c);
			}

			in.close();
			urlconn.disconnect();

			strResult = temp.toString();

		} catch (ActionMessagesException e) {
			/*---------------------------------------------------
				* 業務例外（@Execute#inputへ遷移。自動ロールバック。）
				*--------------------------------------------------*/
			throw e;

		} catch (JJSystemException e) {
			/*---------------------------------------------------
				* システム例外（web.xml#エラー画面へ遷移。自動ロールバック。）
				*--------------------------------------------------*/
			logger.error(e.getMessage(), e);
			throw e;

		} catch (Exception e) {
			/*---------------------------------------------------
				* 想定外例外（web.xml#エラー画面へ遷移。自動ロールバック。）
				*--------------------------------------------------*/
			logger.error(e.getMessage(), e);
			form.err = e.getMessage();


		} finally {
			/*---------------------------------------------------
				* リソース開放処理があればここへ記述。
				*--------------------------------------------------*/
		}

		if (strResult == null || "".equals(strResult))
		{
			return "JJ901SOLR00101.jsp";
		}else
		{
			out.print(strResult);
		}
		out.flush();
		out.close();
		return null;
	}

	class HttpAuthenticator extends Authenticator {
		private String username;
		private String password;
		public HttpAuthenticator(String username, String password){
			this.username = username;
			this.password = password;
		}
		protected PasswordAuthentication getPasswordAuthentication(){
			return new
				PasswordAuthentication(username, password.toCharArray());
		}
		public String myGetRequestingPrompt(){
			return super.getRequestingPrompt();
		}
	}
}
