<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<title>ウィルスチェックレスポンス確認ツール</title>
<jj:css rel="stylesheet" type="text/css" href="${f:url('/style/common.css')}" />
<jj:css rel="stylesheet" type="text/css" href="${f:url('/style/blue/style.css')}" />
<jj:script src="${f:url('/js/jquery.js')}" />
<jj:script src="${f:url('/js/jquery-1.2.6.js')}" />
<jj:script src="${f:url('/js/jquery.tablesorter.js')}" />
</head>
<body>
	<h1>ウィルスチェックレスポンス確認ツール</h1>
	<r2:form method="POST">
		対象ファイル保持ディレクトリ：${f:h(checkDir)}<br />
		対象ファイル数：${f:h(fileCnt)}<br /><br />

		<r2:button value="表示更新" onclick="javascript:index();"/>
		<r2:button value="ウィルスチェック実行" onclick="javascript:check();"/><br /><br />

		<table id="table" style="${f:h(style)}">
			<tr>
				<th style="width:20%; text-align:left;">結果</th>
				<td style="width:80%"></td>
			</tr>
			<tr>
				<th style="width:20%; text-align:left;">チェック開始時刻：</th>
				<td style="width:80%">${f:h(startTime)}</td>
			</tr>
			<tr>
				<th style="width:20%; text-align:left;">チェック完了時刻：</th>
				<td style="width:80%">${f:h(endTime)}</td>
			</tr>
			<tr>
				<th style="width:20%; text-align:left;">チェック対象ファイル数：</th>
				<td style="width:80%">${f:h(fileCnt)}</td>
			</tr>
			<tr>
				<th style="width:20%; text-align:left;">ウィルスなし：</th>
				<td style="width:80%">${f:h(checkOffCnt)}</td>
			</tr>
			<tr>
				<th style="width:20%; text-align:left;">ウィルスあり：</th>
				<td style="width:80%">${f:h(checkOnCnt)}</td>
			</tr>
			<tr>
				<th style="width:20%; text-align:left;">チェック不可：</th>
				<td style="width:80%">${f:h(checkCancelCnt)}</td>
			</tr>
		</table>
	</r2:form>
</body>
<script type="text/javascript">
function index() {
	var form = document.forms['JJ901SOPHOSCHECKActionForm'];
	form.action = 'index';
	form.submit();
}
function check() {
	var form = document.forms['JJ901SOPHOSCHECKActionForm'];
	form.action = 'check';
	form.submit();
}
</script>
</html>