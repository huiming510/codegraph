<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<style type="text/css">
	textarea{
		width:90%;
		height:80%;
	}
</style>
<title>File一覧取得</title>
<jj:css rel="stylesheet" type="text/css" href="${f:url('/style/common.css')}" />
<jj:css rel="stylesheet" type="text/css" href="${f:url('/style/blue/style.css')}" />
</head>

<body>
<h1>File一覧取得</h1>

<r2:form method="get">
表示行数を指定する（指定なし可）：
<input type="hidden" name="strPath" value="${f:h(strPath)}">
<input type="hidden" name="cd" value="${f:h(cd)}">
<input type="text" name="line" value="${f:h(line)}" size="4">
<input type="submit" value="再読み込み">
</r2:form>
<textarea name="fileContent" rows="40" cols="150">
${f:h(fileContent)}
</textarea>

<br/>
ファイル行数：${f:h(totalRow)}

<br/>
${strErr}

</body>
</html>