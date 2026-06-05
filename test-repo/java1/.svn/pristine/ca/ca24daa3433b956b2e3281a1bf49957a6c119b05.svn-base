<!DOCTYPE HTML>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<title>SQL実行ツール</title>
<jj:css rel="stylesheet" href="${f:url('/common/css/animate.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/common.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/index.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/sqltool.css')}" />
</head>

<body>
<div class="header">
	<div class="container row">
		<div class="col-md-8">
			<h1 class="balloon fadeInUp animated"><a href="/unyo-tool/JJ901SQL001/" target="_blank" id="js-sqllink">SQL実行ツール</a></h1>
		</div>
		<div class="col-md-4 suumo01">
			<img class="lightSpeedIn animated" src="/unyo-tool/common/img/suumo_01.png">
		</div>
	</div>
</div>
<div class="sql001-container">
	<%-- ヘッダー表示 --%>
	<div class="sql001-dbkanri-link"><a href="http://wwwtst.unyotool.suumo.jp/db-kanri-tool/toMenu/?userId=cits&kengenKbn=1" target="_blank">ＤＢ管理ツールへのリンク</a></div>
	<div style="display:none;"><form id="js-sqlOpenWindowForm" method="POST" action="/unyo-tool/JJ901SQL001/" target="_blank"></form></div>
	<div class="sql001-infomation">
		<div class="sql001-infomation-click" id="js-balloon">注意事項</div>
	</div>
	<div class="sql001-infomation">
		<div class="sql001-infomation-click" id="js-saveSqlWindow">SQLの保存</div>
	</div>
	<div class="sql001-infomation">
		<ul class="balloon-top" style="display:none;">
			<li>※Excel出力は他のファイル出力処理よりメモリ容量を圧迫するので、大量データを取得するSQL実行はお控えください。</li>
			<li>※課題がある場合はこちら：【運用ツール】SQL実行ツール_課題管理表.xlsx（DevnetID:147231206）</li>
		</ul>
	</div>

	<%-- 設定表示 --%>
	<div class="sql001-inputarea" id="js-operationArea">
		<r2:form styleId="js-sqlInputForm" method="POST">
			<div class="sql001-env">
				<dl class="sql001-choose-server">
					<dt>環境：</dt>
					<dd><r2:select property="server">
						<r2:option value="INSPECTION01">第1検品</r2:option>
						<r2:option value="INSPECTION02">第2検品</r2:option>
						<r2:option value="INSPECTION03">第3検品</r2:option>
						<r2:option value="INSPECTION04">第4検品</r2:option>
						<r2:option value="INSPECTION05">第5検品</r2:option>
						<r2:option value="INSPECTION06">第6検品</r2:option>
						<r2:option value="INSPECTION07">第7検品</r2:option>
						<r2:option value="INSPECTION08">第8検品</r2:option>
						<r2:option value="INSPECTION09">第9検品</r2:option>
						<r2:option value="INSPECTIONSA">第SA検品</r2:option>
						<r2:option value="INSPECTIONSB">第SB検品</r2:option>
						<r2:option value="INSPECTIONSC">第SC検品</r2:option>
					</r2:select></dd>
				</dl>
				<dl class="sql001-choose-db">
					<dt>ＤＢ：</dt>
					<dd><r2:select property="db">
						<r2:option value="FRONT">フロント</r2:option>
						<r2:option value="NYUKO">入稿</r2:option>
						<r2:option value="LOG">ログ</r2:option>
						<r2:option value="KISS">KISS</r2:option>
						<r2:option value="FUJIYAMA">FUJIYAMA</r2:option>
						<r2:option value="RTZ">物サポ</r2:option>
						<r2:option value="MSCRM">MSCRM</r2:option>
						<r2:option value="CHINTAI_PREVIEW">賃貸プレビュー(10g)</r2:option>
						<r2:option value="SNET">SNET賃貸</r2:option>
					</r2:select></dd>
				</dl>
				<dl>
					<r2:submit styleClass="submit-button w200" property="select" value="SQL実行（画面出力）" styleId="js-submitSelect" />
					<r2:submit styleClass="submit-button w100" property="autotrace" value="実行計画" />
				</dl>
			</div>
			<div class="sql001-filedownload">
				<dl class="sql001-choose-downloadExtension">
					<dt>ファイル出力形式：</dt>
					<dd>
						<label><input type="radio" name="downloadExtension" value="tsv" checked="checked" />TSV形式</label>
						<label><input type="radio" name="downloadExtension" value="csv" />CSV形式</label>
						<label><input type="radio" name="downloadExtension" value="excel" />EXCEL形式</label>
					</dd>
				</dl>
				<dl class="sql001-choose-charset">
					<dt>出力文字コード：</dt>
					<dd>
						<label><input type="radio" name="charSet" value="MS932" checked="checked" />MS932</label>
						<label><input type="radio" name="charSet" value="UTF-8" />UTF-8</label>
					</dd>
				</dl>
				<dl><r2:submit styleClass="submit-button w200" property="fileDownload" value="ファイル出力" /></dl>
			</div>

			<div class="sql001-input-sql">
				<r2:textarea styleId="js-inputSqlArea" property="sql" rows="25" />
			</div>

			<div id="up" style="display: none">
				※挿入、更新と削除の操作を行うなら、検証コードを入力してください。<br> 検証コード:
				<r2:text property="key" />
				<br />
				<r2:submit styleClass="submit" property="update" value="更新" />
			</div>
		</r2:form>
	</div>

	<%-- 結果表示 --%>
	<r2logic:notEmpty name="dispMessage">
		<div class="dispMessage">実行結果：${dispMessage}</div>
	</r2logic:notEmpty>
	<r2logic:notEqual name="resultCount" value="-1">
		<div>検索結果：<span class="resultCount">${resultCount}件</span>（${sqlExecuteTimeMills}ミリ秒）</div>
	</r2logic:notEqual>

	<r2logic:notEmpty name="dispColumnValueList">
		<div class="sql001-outputarea">
			<table id="js-outputtable" border="1">
				<thead>
					<tr>
						<r2logic:iterate id="columnName" name="dispColumnName">
							<td><r2:write name="columnName" /></td>
						</r2logic:iterate>
					</tr>
				</thead>
				<tbody>
					<r2logic:iterate id="columnValueList" name="dispColumnValueList">
						<tr>
							<r2logic:iterate id="columnValue" name="columnValueList">
								<td>${f:h(columnValue)}</td>
							</r2logic:iterate>
						</tr>
					</r2logic:iterate>
				</tbody>
			</table>
		</div>
	</r2logic:notEmpty>
</div>

<div class="localStorageSQL">
	<div>
		<p id="localStorageSQLTitle">SQLの保存</p>
		<p id="js-closeSaveSqlWindow"><span>閉じる</span></p>
		<p>名前を付けてSQLをlocalStorageに保存</p>
		<input placeholder="名前を入力してください" id="js-inputSqlName"/>
		<button type="button" id="js-saveLocalStorage" class="submit-button">保存</button>
	</div>
	<div class="sqlList">
		<strong>SQLリスト</strong>
		<ul>
		</ul>
	</div>
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

	// 共有事項展開
	$('#js-balloon').click(function() {
		$('.balloon-top').toggle();
	});

	// 画面複製
	$('#js-sqllink').click(function() {
		$('#js-sqlOpenWindowForm').empty();
		$('#js-sqlInputForm').contents().clone().appendTo('#js-sqlOpenWindowForm');
		$('#js-sqlOpenWindowForm').submit();
		return false;
	});

	$(window).load(function() {
		// インプットエリアのauto focus
		$('#js-inputSqlArea').focus();

		// SQL実行　ショートカット（CTRL＋ENTER）
		$('#js-inputSqlArea').keydown(function(e) {
			if (event.ctrlKey && e.keyCode == 13) {
				$('#js-submitSelect').click();
			};
		});

		// テーブルのヘッダー固定
		$('#js-outputtable').floatThead({
			position: "absolute",
		});

		// テーブルのカラー表示
		$('tbody tr').hover(function() {
			$(this).css('background', '#90EE90');
		}, function() {
			$(this).css('background', '');
		});
		$('tbody tr').click(function() {
			let $target = $(this);
			if ($target.hasClass('tableClickColor')) {
				$(this).removeClass('tableClickColor');
			} else {
				$(this).addClass('tableClickColor');
			};
		});

		////////////////////
		//sql localStorage//
		///////////////////
		//localStorageに保存されているSQLを表示
		localStorageSqlDisp();

		//localStorage 保存処理//
		$('#js-saveLocalStorage').click(function() {
			//SQL名 空判定
			if (!$('#js-inputSqlName').val()) {
				alert("名前を入力してください");
				return;
			}

			var sqlObj = {};
			//localStorage sqlList から判定
			if (localStorage.getItem("sqlList")) {
				//読込
				var getjson = localStorage.getItem("sqlList");
				var sqlObj = JSON.parse(getjson);
			}

			////上書き判定////
			var sqlNameNew = escapeHtml($('#js-inputSqlName').val());

			var result = true;
			for(var sqlName in sqlObj){
				if (sqlNameNew == sqlName) {
					result = window.confirm("すでに" + escapeJS(sqlNameNew) + "が存在しますが、上書きしますか？");
				}
			}
			//保存処理
			if (result) {
				sqlObj[sqlNameNew] = escape($('#js-inputSqlArea').val());
				var setjson = JSON.stringify(sqlObj);
				localStorage.setItem("sqlList", setjson);
				//localStorageに保存されているSQLを表示
				localStorageSqlDisp();
			}
		});

		//SQLリストを表示
		$('#js-saveSqlWindow').click(function(){
			if ($('div.localStorageSQL').css("display") == "none") {
				$('div.localStorageSQL').fadeIn();
			} else {
				$('div.localStorageSQL').fadeOut();
			}
		});

		//SQLリストを閉じる
		$('#js-closeSaveSqlWindow > span').click(function(){
			$('div.localStorageSQL').fadeOut();
		});
	});

	//localStorageに保存されているSQLを表示//
	var localStorageSqlDisp = function(){
		$('div.sqlList > ul').html('');

		var sqlObj = {};
		//localStorage sqlList から判定
		if (localStorage.getItem("sqlList")) {
			//読込
			var getjson = localStorage.getItem("sqlList");
			var sqlObj = JSON.parse(getjson);
		}

		//overflowの切り替え
		var sqlList = document.querySelector("div.sqlList > ul");
		if (Object.keys(sqlObj).length > 8) {
			sqlList.style.height = "270px";
			sqlList.style.overflow = "auto";
		} else {
			sqlList.style.height = "initial";
			sqlList.style.overflow = "initial";
		}

		//値の表示
		for(var sqlName in sqlObj){
			$('div.sqlList > ul').html(
				$('div.sqlList > ul').html()
				+ "<li><span onclick='writeSql(\"" + sqlObj[sqlName] + "\")'>"
				+ sqlName
				+ "</span><button type='button' class='submit-button' onclick='removeSql(\"" + escapeHtml(sqlName) + "\")'>削除</button></li>"
			);
		}
	}

	//localStorgeのsql　削除
	function removeSql(sqlName){
		sqlName = escapeJS(sqlName);
		var result = window.confirm("本当に" + sqlName + "を削除しますか？");

		if (result) {
			//localStorage 読込
			var getjson = localStorage.getItem("sqlList");
			var sqlObj = JSON.parse(getjson);
			//削除処理
			delete sqlObj[escapeHtml(sqlName)];
			//保存
			var setjson = JSON.stringify(sqlObj);
			localStorage.setItem("sqlList", setjson);
			//localStorageに保存されているSQLを表示
			localStorageSqlDisp();
		}
	}

	//write sql
	function  writeSql(sql){
		sql = unescape(sql);
		var sqlArea = document.getElementById("js-inputSqlArea");
		sqlArea.value = sql;
	}

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
