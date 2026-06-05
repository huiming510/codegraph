package jp.co.rct.jj.action;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;

import javax.annotation.Resource;

import jp.co.rct.jj.form.JJ901FCHK001Form;

import org.seasar.struts.annotation.ActionForm;
import org.seasar.struts.annotation.Execute;


public class JJ901FCHK001Action {

    /** コード範囲(全角記号① 開始) */
    int AREA_MARK_1_START = 0x8740;
    /** コード範囲(全角記号Ⅹ 終了) */
    int AREA_MARK_1_END = 0x875D;

    /** コード範囲(全角記号㍉ 開始) */
    int AREA_MARK_2_START = 0x875F;
    /** コード範囲(全角記号㎡ 終了) */
    int AREA_MARK_2_END = 0x8775;

    /** コード範囲(全角記号㍻ 開始) */
    int AREA_MARK_3_START = 0x877E;
    /** コード範囲(全角記号∪ 終了) */
    int AREA_MARK_3_END = 0x879C;

    /** コード範囲(全角記号纊 開始) */
    int AREA_MARK_4_START = 0xED40;
    /** コード範囲(全角記号黑終了) */
    int AREA_MARK_4_END = 0xEEEC;

    /** コード範囲(全角記号ⅰ開始) */
    int AREA_MARK_5_START = 0xEEEF;
    /** コード範囲(全角記号＂ 終了) */
    int AREA_MARK_5_END = 0xEEFC;

    /** コード範囲(全角記号ⅰ開始) */
    int AREA_MARK_6_START = 0xFA40;
    /** コード範囲(全角記号黑終了) */
    int AREA_MARK_6_END = 0xFC4B;

    @ActionForm
    @Resource(name = "JJ901FCHK001Form")
    private JJ901FCHK001Form form;

    public String strContent;
    public String strResult;
    public String strContent2;


    StringBuffer sbMoji = new StringBuffer();

    @Execute(validator = false)
    public String index() {

    	String strErr="";

        FileInputStream in = null;
        InputStreamReader isr = null;
        BufferedReader br = null;
        String str = null;

        StringBuffer sb = new StringBuffer();
		try
		{            // 入力ファイル指定

            in = new FileInputStream(form.filePath);

            String strCd="Shift-JIS";
            if (form.code != null && !"".equals(form.code))
            {
            	strCd = form.code;
            }

            isr = new InputStreamReader(in, strCd);
            br = new BufferedReader(isr);

            while ((str = br.readLine()) != null) {
                sb.append(str);
            }

            String templateStr = sb.toString();
            strContent2=templateStr;

            strResult=checkStr(templateStr);
			strContent=sbMoji.toString();

		}catch(Exception e)
		{
			strErr=e.getMessage();
		}
		form.strErr = strErr;
    	return "JJ901FCHK00101.jsp";
    }

    public String checkStr(String adInfo) {

        //機種依存文字を格納する
        StringBuffer errMoji = new StringBuffer("");

        if (existValue(adInfo)) {
            try {
                for (int i = 0; i < adInfo.length(); i++) {
                    String cutStr = Character.toString(adInfo.charAt(i));
                    if (isUsableLargeCharIncludeEnterAndTab(cutStr)) {
                        continue;
                    } else {
                        errMoji.append(cutStr);
                    }
                }
            } catch (UnsupportedEncodingException e) {
            }
        }

        return errMoji.toString();
    }

    public boolean existValue(String str) {

        if (isNull(str) || isBlank(str)) {
            return false;
        } else {
            return true;
        }
    }

    private boolean isErrMoji(char ch) {

        if (compareCode(ch, AREA_MARK_1_START, AREA_MARK_1_END) || compareCode(ch, AREA_MARK_2_START, AREA_MARK_2_END)
                || compareCode(ch, AREA_MARK_3_START, AREA_MARK_3_END)
                || compareCode(ch, AREA_MARK_4_START, AREA_MARK_4_END)
                || compareCode(ch, AREA_MARK_5_START, AREA_MARK_5_END)
                || compareCode(ch, AREA_MARK_6_START, AREA_MARK_6_END)) {
            return true;
        } else {
            return false;
        }
    }

    public boolean isNull(String str) {

        if (str == null) {
            return true;
        } else {
            return false;
        }
    }

    public boolean isBlank(String str) {

        if ("".equals(str)) {
            return true;
        } else {
            return false;
        }
    }

    private boolean compareCode(char ch, int startCode, int endCode) {

        return (ch >= startCode && ch <= endCode);
    }

    private boolean isUsableLargeCharIncludeEnterAndTab(String str) throws UnsupportedEncodingException {

        char ch = convertToChar(str);
        if (isErrMoji(ch)) {
            return false;
        } else
            return true;
    }


    private char convertToChar(String str) throws UnsupportedEncodingException {

        char firstChar = 0;
        char lastChar = 0;

        sbMoji.append("convertToChar:"+str+"\n");
        byte[] bStr = str.getBytes("Windows-31J");


        if (bStr.length == 2) {
            firstChar = (char) bStr[0];
            lastChar = (char) bStr[1];
            firstChar <<= 8;
            lastChar <<= 8;
            lastChar >>= 8;
        } else if (bStr.length == 1) {
            firstChar = (char) bStr[0];
            firstChar <<= 8;
            firstChar >>= 8;
            sbMoji.append("return convertToChar:"+Integer.toHexString((int)firstChar) + "\n");
            return firstChar;
        }
        sbMoji.append("return convertToChar:"+Integer.toHexString((int)(char) (firstChar + lastChar))+"\n");
        return (char) (firstChar + lastChar);
    }

}
