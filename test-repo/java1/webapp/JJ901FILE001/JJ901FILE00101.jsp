<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<title>File一覧取得</title>
<jj:css rel="stylesheet" href="${f:url('/common/css/animate.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/common.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/index.css')}" />
<jj:css rel="stylesheet" type="text/css" media="all" href="${f:url('/common/css/jquery.dataTables.css')}" />
<jj:script src="${f:url('/common/js/jquery-3.2.1.min.js')}" type="text/javascript" />
<jj:script src="${f:url('/common/js/jquery.dataTables.js')}" type="text/javascript" />
<jj:script src="${f:url('/common/js/currency.js')}" type="text/javascript" />
<script language="JavaScript" type="text/javascript">
	function open_win(object, target) {
		SubWindow = window
				.open(
						object,
						target,
						"width=1200,top=0,left=0,toolbar=1,location=1,status=1,menubar=1,scrollbars=1,resizable=1");
		SubWindow.focus();
	}
</script>
</head>

<body>
	<div class="header">
		<div class="container">
			<div class="row">
				<div class="col-md-8">
					<h2 class="balloon fadeInUp animated">サーバーファイル一覧（バージョン:1.0）</h2>
				</div>
				<div class="col-md-4 suumo01">
					<img class="lightSpeedIn animated" src="../common/img/suumo_01.png">
				</div>
			</div>
		</div>
	</div>
	<r2:form method="get">

			<p class="input-serverpath">サーバーディレクトリパスを入力してください。ファイルパスでも1件検索ができます：</p>
			<div style="display:flex;">
				<r2:text styleClass="input-serverpath" property="strPath" size="100" />
				<r2:submit property="index" value="検索" />
				<button type="button" id="tableDL" style="display: block; margin: 0 5vw 0 auto;">表示内容 DL</button>
			</div>
		<r2:size id="dirCount" name="dirList" />
		<r2:size id="fileCount" name="fileList" />

		<%
			if (dirCount + fileCount > 0) {
		%>
		<div style="width: 90vw; margin: 10px auto;">
			<table id="fileListTable" border="1" class="cell-border compact nowrap order-column">
				<thead>
					<tr>
						<th>名前</th>
						<th>サイズ</th>
						<th>更新日時</th>
						<th>OPEN</th>
						<th>DOWNLOAD</th>
					</tr>
				</thead>
				<tbody>

					<r2logic:iterate id="dirValue" name="dirList" offset="0">
						<tr>
							<r2:define id="fileName" value="${f:h(dirValue.fileName)}"
								type="java.lang.String" />
							<r2:define id="filePath" value="${f:h(dirValue.filePath)}"
								type="java.lang.String" />
							<td>&nbsp;<a
								href="/unyo-tool/JJ901FILE001/?strPath=${filePath}">${f:h(fileName)}</a></td>
							<td data-order="0">&nbsp;<r2:write name="dirValue" property="fileSize" /></td>
							<td class="dt-center">&nbsp;<r2:write name="dirValue"
									property="fileModify" /></td>
							<td class="dt-center">&nbsp;</td>
							<td class="dt-center">&nbsp;</td>
						</tr>
					</r2logic:iterate>

					<r2logic:iterate id="fileValue" name="fileList">
						<tr>
							<r2:define id="fileName" value="${f:h(fileValue.fileName)}" type="java.lang.String" />
							<r2:define id="filePath" value="${f:h(fileValue.filePath)}" type="java.lang.String" />

							<td>&nbsp;<r2:write name="fileValue" property="fileName" /></td>
							<td data-order="<r2:write name="fileValue" property="fileSize" />" class="dt-right">&nbsp;<r2:write name="fileValue" property="fileSize" /></td>
							<td class="dt-center">&nbsp;<r2:write name="fileValue" property="fileModify" /></td>
							<td class="dt-center"><a href=""
								onClick="javascript:open_win('/unyo-tool/JJ901OPEN001/?strPath=${filePath}&cd=u',''); return false;">表示(UTF)</a>
								| <a href=""
								onClick="javascript:open_win('/unyo-tool/JJ901OPEN001/?strPath=${filePath}&cd=s',''); return false;">表示(SHIFT)</a>|
								<a href=""
								onClick="javascript:open_win('/unyo-tool/JJ901FCHK001/?filePath=${filePath}',''); return false;">CHECK</a></td>
							<td class="dt-center"><a
								href="/unyo-tool/JJ901FILE001/download?strPath=${filePath}">download</a>
							</td>
						</tr>
					</r2logic:iterate>
				</tbody>
			</table>
		</div>
		<%
			}
		%>
		<br />
${strErr}
</r2:form>
	<script type="text/javascript">
	<!--
		$(function() {
			$("#fileListTable").DataTable({
				columnDefs: [{ type: 'currency', targets: [1] }], // サイズを数値ソートする
				paging: false, // ページングしない
				scrollY: '65vh', // ヘッダ固定して縦スクロールする
				order: [[ 0, "asc" ]], // 初期ソート指定
				stateSave: true, // 更新時に状態を固定する
				scrollCollapse: true, // 行数少ないときに詰める
			});

			////////////////////
			//表示内容Download//
			////////////////////
			$("#tableDL").click(function(){
				var data = tableData().map((v) => v.join('\t')).join('\r\n');
				var bom = new Uint8Array([0xEF, 0xBB, 0xBF]);
				var blob = new Blob([bom, data], {type: 'text/tsv'});
				var url = window.URL.createObjectURL(blob);
				var link = document.createElement('a');
				link.download = 'result.tsv';
				link.href = url;
				document.body.appendChild(link);
				link.click();
				document.body.removeChild(link);
			});

		});

		var tableData = function(){
			var table = [];

			//theadの取得
			var array = Array.from(document.querySelectorAll("#fileListTable thead tr th"));
			//OPEN DOWNLOADは取得しないので、削除
			array.splice(3,2);
			var arr = array.map((v) => v.innerText);
			table.push(arr);

			//tbodyの取得
			document.querySelectorAll("#fileListTable tbody tr").forEach(function(value){
				var array = Array.from(value.querySelectorAll("td"));
				//OPEN DOWNLOADは取得しないので、削除
				array.splice(3,2);
				var arr = array.map((v) => v.innerText.trim());
				table.push(arr);
			});

			return table;
		};
	//-->
	</script>
</body>
</html>
