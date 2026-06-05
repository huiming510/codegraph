package jp.co.rct.jj.action;

import java.util.Arrays;
import java.util.Comparator;

import javax.annotation.Resource;
import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import jp.co.rct.jj.base.env.EnvValueDefineUtil;
import jp.co.rct.jj.form.JJ901COOKIE001Form;

import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;

public class JJ901COOKIE001Action {

	/** リクエスト */
	@Resource
	protected HttpServletRequest request;

	/** レスポンス **/
	@Resource
	protected HttpServletResponse response;

	@ActionForm
	@Resource(name = "JJ901COOKIE001Form")
	protected JJ901COOKIE001Form form;

	public String envName;
	public Cookie cookies[];

	/* Cookie表示 */
	@Execute(validator = false)
	public String index() {
		envName = EnvValueDefineUtil.getValue("KENPIN_NAME");
		cookies = request.getCookies();

		Arrays.sort(cookies, new Comparator<Cookie>() {
			public int compare(Cookie cookie1, Cookie cookie2) {
				return cookie1.getName().toUpperCase().compareTo(cookie2.getName().toUpperCase());
			}
		});

		return "JJ901COOKIE001.jsp";

	}

	/* Cookie更新 */
	@Execute(validator = false)
	public String updateCookie() {
		Cookie cookie = getCookie(form.cookieName);

		if (cookie != null) {
			cookie.setPath("/");
			cookie.setValue(form.cookieValue == null ? "" : form.cookieValue);
		}
		response.addCookie(cookie);
		return "/JJ901COOKIE001/?redirect=true";
	}

	/* 名前が一致するCookieを取得 */
	private Cookie getCookie(String name) {
		Cookie cookies[] = request.getCookies();

		if (cookies == null || name == null || name.length() == 0) {
			return null;
		}

		for (int i = 0; i < cookies.length; i++) {
			if (name.equals(cookies[i].getName())) {
				return cookies[i];
			}
		}

		return null;
	}

}