package jp.co.rct.jj.action;

import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;

import javax.annotation.Resource;
import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.seasar.struts.annotation.Execute;

public class DebugPrintAction {

    public boolean isDebugPrint;

    @Resource
    HttpServletRequest request;

    @Resource
    HttpServletResponse response;

    /**
     * 初期表示メソッド
     * <pre>
     * 初期画面表示時に実行されるメソッド
     * URLに直接指定しない場合、デフォルトでindex()が呼ばれる。
     * </pre>
     * @return String 遷移先のパス
     */
    @Execute(validator = false)
    public String index() throws Exception {

        isDebugPrint = false;
        Cookie[] cookies = request.getCookies();
        if (cookies != null) {
            for (Cookie cookie : cookies) {
                if ("isDebugPrint".equals(cookie.getName())) {
                    isDebugPrint = Boolean.parseBoolean(cookie.getValue());
                }
            }
        }
        return "setting.jsp";
    }

    @Execute(validator = false)
    public String execteSetting() {

        try {
            String value = URLEncoder.encode(Boolean.valueOf(isDebugPrint).toString(), "Shift_JIS");
            Cookie additionalCookie = new Cookie("isDebugPrint", value);
            additionalCookie.setPath("/");
            response.addCookie(additionalCookie);
        } catch (UnsupportedEncodingException e) {
            e.printStackTrace();
        }
        return "result.jsp";
    }

}
