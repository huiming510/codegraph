<!DOCTYPE HTML>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<link rel="stylesheet" href="/unyo-tool/common/css/cookie.css" />

<title>Cookie表示＆更新ツール</title>

</head>

<body>
	<h1>${envName}検品　Cookie表示＆更新ツール</h1>
	<p>注意点：.suumo.jpのCookieを変更した場合は、wwwtst.suumo.jp等の完全一致ドメインで同名Cookieが追加されます。(.suumo.jpのCookie更新にはならない)</p>
	<div class="wrapper">
		<table>
			<thead>
				<tr>
					<th></th>
					<th>名前</th>
					<th>値</th>
				</tr>
			</thead>
			<tbody>
				<r2logic:iterate name="cookies" id="cookies">
				    <r2:form action="updateCookie" method="post">
						<tr>
							<td>
								<input type="submit" name="hoge" value="変更" class="js-update"/>
							</td>
							<td class="cookieName">
								<r2:write name="cookies" property="name"  />
								<r2:hidden property="cookieName" value="${cookies.name}" />
							</td>
							<td>
								<r2:write name="cookies" property="value"  /><br>
								<r2:textarea style="width:90%;" property="cookieValue" value="${cookies.value}"/>
							</td>
						</tr>
					</r2:form>
				</r2logic:iterate>
			</tbody>
		</table>
	</div>
	<jj:script src="${f:url('/common/js/jquery-3.2.1.min.js')}" />
	<jj:script src="${f:url('/common/js/cookie.js')}" />
</body>
</html>