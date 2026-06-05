<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<title>FileUpload結果</title>
<jj:css rel="stylesheet" type="text/css" href="${f:url('/style/common.css')}" />
<jj:css rel="stylesheet" type="text/css" href="${f:url('/style/blue/style.css')}" />
</head>

<body>
	<c:if test="${null == strErr || '' == strErr}" >
		OK<br/>
		${fileUp}
	</c:if>
	<c:if test="${null != strErr && '' != strErr}" >
		ERROR<br/>
		${strErr}
	</c:if>
</body>
</html>