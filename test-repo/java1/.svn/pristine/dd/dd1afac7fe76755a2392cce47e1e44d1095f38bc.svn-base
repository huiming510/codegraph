<!DOCTYPE HTML>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<r2logic:equal name="resultStatus" value="-1">
	<meta http-equiv="refresh" content="10;URL=/unyo-tool/JJ901APITEST001/reload/">
</r2logic:equal>
<title>APIテスト実行ツール（賃貸用）</title>
<jj:css rel="stylesheet" href="${f:url('/common/css/animate.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/common.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/index.css')}" />
<style>
div {
	display: block;
}

li {
	list-style: none;
}

dt {
	float: left;
}

dd {
	margin-left: 80px;
}

.apitest-header{
	background: #6cd570;
	min-width: 1000px;
}

.result_table {
	border: 5px double black;
	width: 1000px;
}

.table_th {
	border: 2px solid black;
	background: #007700;
	color: #ffffff;
}

.table_td {
	border: 2px solid black;
}

.alert-top{
	position: relative;
	display:none;
	margin: 1.5em 0;
	padding: 5px 10px;
	min-width: 150px;
	max-width: 100%;
	color: #555;
	font-size: 16px;
	background: #e0edff;
}

.subject {
	margin: 20px 50px;
	background: #fff;
	width: auto;
	min-width: 200px;
	border-radius: 20px;
	text-align: left;
	text-decoration:underline;
	color: #4caf50;
	font-size: 30px;
	text-shadow: 2px 2px #aadf41;
}

.execute_button{
	padding: 10px 20px;
	margin: 5px 20px;
	cursor: pointer;
	color: #FFFFFF;
	text-shadow: -1px -1px 1px #dd6200, 0 1px 1px #f88c20;
	background-color: #F77C00;
	border-bottom: 2px solid #D26A00;
	border-radius: 2px;
	box-shadow: 0 2px 1px #d9d9d9;
}

.message {
	padding: 10px 50px;
	position: relative;
	clear: both;
	width: 100%;
	font-size: 20pt;
	font-weight: bold;
	color: red;
}

.download_button {
	padding: 5px 20px;
	margin: 5px 5px;
	cursor: pointer;
	color: #FFFFFF;
	text-shadow: -1px -1px 1px #dd6200, 0 1px 1px #f88c20;
	background-color: #F77C00;
	border-bottom: 2px solid #D26A00;
	border-radius: 2px;
	box-shadow: 0 2px 1px #d9d9d9;
}

.download_button_disable {
	padding: 5px 20px;
	margin: 5px 5px;
	cursor: pointer;
	color: #000000;
	opacity: 0.5;
	background-color: #DDDDDD;
	border-radius: 2px;
	box-shadow: 0 2px 1px #d9d9d9;
}
</style>
</head>

<body>
<div class="apitest-header">
	<div style="overflow: hidden;padding: 15px 15px;">
		<div style="position: relative;min-height: 1px;float: left;">
			<h1 style="right: 0;background: #fff;width: auto;min-width: 200px;padding: 15px 50px;border-radius: 60px;text-align: center;text-shadow: 2px 2px #aadf41;">
			<a href="/unyo-tool/JJ901APITEST001/" target="_blank" style="font-size: 30px; color:#4caf50">賃貸APIノンデグレテスト実行ツール</a></h1>
		</div>
		<div style="position: relative;min-height: 1px;float: left;">
			<img style="vertical-align: middle;border: 0;height: 80px;" src="/unyo-tool/common/img/suumo_01.png">
		</div>
	</div>
</div>
<div>
	<%-- ヘッダー表示 --%>
	<div style="padding: 30px 30px;font-size: 24px;display: inline;">
		<a href="https://wwwtst.suumo.jp/unyo-tool/" target="_blank">開発環境用ツールへのリンク</a>
	</div>
	<div style="padding: 30px 30px;font-size: 24px;display: inline;">
		<div style="text-decoration: underline;color: #337ab7;cursor: pointer;display: inline-block;" id="js-alert">注意事項(クリックして展開)</div>
	</div>
	<div style="margin: 15px;font-size: 24px;display: block;">
		<ul class="alert-top">
			<li>テストケースが多いため、特に物件検索API（V4）はテスト実行に数分かかることがあります</li>
			<li>テストが正常に実行されない可能性があるため、絶対に「実行」ボタンを連打しないでください</li>
			<li>※テストツールの利用方法詳細はこちら（DocumentID：8f0fd3bb-022c-4878-b382-5261ebacd8e3）</li>
			<li>※レスポンスに差分がある場合はこちらのメンテナンス手順書を参考にレスポンスの期待値を更新してください（DocumentID：08a134c4-1f3c-407d-be84-b7b893fa79ab）</li>
		</ul>
	</div>
	<%-- 設定表示 --%>
	<div>
		<h1 class ="subject">テスト対象選択</h1>
	</div>
	<div style="width: 100%;display: block">
		<r2:form method="POST">
			<div style="width: 500px;float: left;font-size: 18px;">
				<dl style="margin: 15px 50px;">
					<dt>環　境：</dt>
					<dd><r2:select property="env">
						<%-- <r2:option value="1">第1検品</r2:option>
						<r2:option value="2">第2検品</r2:option> --%>
						<r2:option value="3">第3検品</r2:option>
						<%-- <r2:option value="4">第4検品</r2:option>
						<r2:option value="5">第5検品</r2:option>
						<r2:option value="6">第6検品</r2:option>
						<r2:option value="7">第7検品</r2:option>
						<r2:option value="8">第8検品</r2:option>
						<r2:option value="9">第9検品</r2:option> --%>
					</r2:select></dd>
				</dl>
				<dl style="margin: 15px 50px;">
					<dt>ＡＰＩ：</dt>
					<dd><r2:select property="api">
						<r2:option value="bknapi">物件検索ＡＰＩ(Ｖ４)</r2:option>
						<r2:option value="shsapi">賃貸詳細ＡＰＩ</r2:option>
						<r2:option value="cstapi">賃貸カセットＡＰＩ</r2:option>
					</r2:select></dd>
				</dl>
				<dl style="display:flex;margin: 30px 50px;">
					<r2:submit styleClass="execute_button" property="execute" value="テスト実行（画面出力）"></r2:submit>
				</dl>
			</div>
		</r2:form>
	</div>
	<%-- 前回テスト実行日付とダウンロードボタン --%>
	<r2logic:notEqual name="resultStatus" value="-1">
		<r2logic:notEqual name="resultStatus" value="2">
			<div style="width: 500px;float: left;font-size: 16px">
				<table class="result_table">
					<tr>
						<th class = "table_th">対象API</th>
						<th class = "table_th">前回テスト実行日時</th>
						<th class = "table_th">ダウンロード</th>
					</tr>
					<tr>
						<td class = "table_td">物件検索API（V4）</td>
						<td class = "table_td">${lastDateTime_bknapi}</td>
						<td style = "text-align: center; border: 2px solid black">
							<r2logic:equal name="lastDateTime_bknapi" value="－">
								<button disabled class = "download_button_disable" onclick="location.href='/unyo-tool/JJ901APITEST001/downloadBknapi'">
								比較結果htmlダウンロード
								</button>
							</r2logic:equal>
							<r2logic:notEqual name="lastDateTime_bknapi" value="－">
								<button class = "download_button" onclick="location.href='/unyo-tool/JJ901APITEST001/downloadBknapi'">
								比較結果htmlダウンロード
								</button>
							</r2logic:notEqual>
						</td>
					</tr>
					<tr>
						<td class = "table_td">賃貸詳細API</td>
						<td class = "table_td">${lastDateTime_shsapi}</td>
						<td style = "text-align: center; border: 2px solid black">
							<r2logic:equal name="lastDateTime_shsapi" value="－">
								<button disabled class = "download_button_disable" onclick="location.href='/unyo-tool/JJ901APITEST001/downloadShsapi'">
								比較結果htmlダウンロード
								</button>
							</r2logic:equal>
							<r2logic:notEqual name="lastDateTime_shsapi" value="－">
								<button class = "download_button" onclick="location.href='/unyo-tool/JJ901APITEST001/downloadShsapi'">
								比較結果htmlダウンロード
								</button>
							</r2logic:notEqual>

						</td>
					</tr>
					<tr>
						<td class = "table_td">賃貸カセットAPI</td>
						<td class = "table_td">${lastDateTime_cstapi}</td>
						<td style = "text-align: center; border: 2px solid black;">
							<r2logic:equal name="lastDateTime_cstapi" value="－">
								<button disabled class = "download_button_disable" onclick="location.href='/unyo-tool/JJ901APITEST001/downloadCstapi'">
								比較結果htmlダウンロード
								</button>
							</r2logic:equal>
							<r2logic:notEqual name="lastDateTime_cstapi" value="－">
								<button class = "download_button" onclick="location.href='/unyo-tool/JJ901APITEST001/downloadCstapi'">
								比較結果htmlダウンロード
								</button>
							</r2logic:notEqual>
						</td>
					</tr>
				</table>
			</div>
		</r2logic:notEqual>
	</r2logic:notEqual>

	<%-- 画面メッセージ表示 --%>
	<r2logic:notEmpty name="dispMessage">
		<div class = "message">${dispMessage}</div>
	</r2logic:notEmpty>

	<%-- 結果表示 --%>
	<r2logic:equal name="resultStatus" value="1">
		<div style="height:800px;width:100%;clear:both;border:10px double #000000;overflow:scroll;">
			<%-- APIテストの結果表示 --%>
			<jj:insert baseEnvName="APITEST_RESULT_FILE_DIR" path="${resultHtmlName}" encoder="UTF-8"/>
		</div>
	</r2logic:equal>
</div>

<jj:script src="${f:url('/common/js/jquery-2.1.1.min.js.pagespeed.jm.OH66oSK0of.js')}" />
<jj:script src="${f:url('/common/js/index.js.pagespeed.jm.IG7crq-Pjj.js')}" />
<jj:script src="${f:url('/common/js/jquery.floatThead.js')}" />

<script>

	window.document.onkeydown = function upDisplay(ev) {
		var curEvent = ev || window.event;
		if (curEvent.keyCode == 192) {
			window.document.getElementById("up").style.display = "block";
		} else if (curEvent.keyCode == 220) {
			window.document.getElementById("up").style.display = "none";
		};
	};

	// 注意事項展開
	$('#js-alert').click(function() {
		$('.alert-top').toggle();
	});

	//escapeHTML
	function escapeHtml(str){
		str = str.replace(/&/g, '&amp;');
		str = str.replace(/>/g, '&gt;');
		str = str.replace(/</g, '&lt;');
		str = str.replace(/"/g, '&quot;');
		str = str.replace(/'/g, '&#x27;');
		str = str.replace(/`/g, '&#x60;');
		str = str.replace(/\\/g, '&yen;');
		return str;
	}

	//escapeJS
	function escapeJS(str){
		str = str.replace(/&amp;/g, "&");
		str = str.replace(/&gt;/g, ">");
		str = str.replace(/&lt;/g, "<");
		str = str.replace(/&quot;/g, '\"');
		str = str.replace(/&#x27;/g, "\'");
		str = str.replace(/&#x60;/g, '\`');
		str = str.replace(/&yen;/g, '\\');
		return str;
	}

</script>

</body>
</html>
