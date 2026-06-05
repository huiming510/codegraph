package jp.co.rct.jj.action;

import java.lang.reflect.Method;
import java.net.URLDecoder;

import javax.annotation.Resource;

import org.apache.commons.lang.StringUtils;
import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;

import jp.co.rct.jj.base.service.solr.QassSelectClientImplEx;
import jp.co.rct.jj.form.JJ901SOLR003Form;
import r2framework.qass.solr.server.QassSolrServer;

/**
 * Elasticsearchのクエリから、検索先インデックスを判定する
 * @author kaisho
 */
public class JJ901SOLR003Action {

	@ActionForm
	@Resource(name = "JJ901SOLR003Form")
	private JJ901SOLR003Form form;

	@Execute(validator = false)
	public String index() {

		if (StringUtils.isEmpty(form.solrQuery)) {
			return "JJ901SOLR00301.jsp";
		}

		QassSelectClientImplEx qassSelectClientImplEx  = new QassSelectClientImplEx();
		qassSelectClientImplEx.setQassSolrServer_CM0001(new QassSolrServer(""));
		qassSelectClientImplEx.setQassSolrServer_CM0002(new QassSolrServer(""));
		qassSelectClientImplEx.setQassSolrServer_SeachALL(new QassSolrServer(""));
		qassSelectClientImplEx.setQassSolrServer_SeachFR(new QassSolrServer(""));
		qassSelectClientImplEx.setQassSolrServer_SeachFR0001(new QassSolrServer(""));
		qassSelectClientImplEx.setQassSolrServer_SeachFR0002(new QassSolrServer(""));

		try {

			Method method = QassSelectClientImplEx.class.getDeclaredMethod("getTargetServer", new Class[] {String.class});
			method.setAccessible(true);

			QassSolrServer result = (QassSolrServer) method.invoke(qassSelectClientImplEx, URLDecoder.decode(form.solrQuery,"UTF-8"));

			if (result == null) form.target = "?";
			else if (result == qassSelectClientImplEx.getQassSolrServer_CM0001()) form.target = "共通１インデックス（CM0001）";
			else if (result == qassSelectClientImplEx.getQassSolrServer_CM0002()) form.target = "共通２インデックス（CM0002）";
			else if (result == qassSelectClientImplEx.getQassSolrServer_SeachALL()) form.target = "横断マルチインデックス（FR0001＆FR0002＆CM0001）";
			else if (result == qassSelectClientImplEx.getQassSolrServer_SeachFR()) form.target = "賃貸マルチインデックス（FR0001＆FR0002）";
			else if (result == qassSelectClientImplEx.getQassSolrServer_SeachFR0001()) form.target = "賃貸関東インデックス（FR0001）";
			else if (result == qassSelectClientImplEx.getQassSolrServer_SeachFR0002()) form.target = "賃貸関東以外インデックス（FR0002）";

		} catch  (Exception e) {
			form.target = "?";
		}

		return "JJ901SOLR00301.jsp";
	}

}
