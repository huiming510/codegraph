<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<title>Elasticsearch取得</title>
<jj:css rel="stylesheet" type="text/css" href="${f:url('/style/common.css')}" />
<jj:css rel="stylesheet" type="text/css" href="${f:url('/style/blue/style.css')}" />
<jj:script src="${f:url('/js/jquery.js')}" />
<jj:script src="${f:url('/js/jquery-1.2.6.js')}" />
<jj:script src="${f:url('/js/jquery.tablesorter.js')}" />
<script type="text/javascript">
<!--

window.document.onkeydown = function upDisplay (ev) {
	var curEvent = ev || window.event;
	if (curEvent.keyCode == 192) {
		window.document.getElementById("up").style.display = "block";
	} else if (curEvent.keyCode == 220) {
		window.document.getElementById("up").style.display = "none";
	}
}

function view() {
	var elem1 = document.getElementById("area1");
	var elem2 = document.getElementById("area2");

	var i;
	if (document.JJ901SOLR001ActionForm.solrRequest.length) {
		for (i = 0; i < document.JJ901SOLR001ActionForm.solrRequest.length; i++) {
			if (document.JJ901SOLR001ActionForm.solrRequest[i].checked) {
				if(document.JJ901SOLR001ActionForm.solrRequest[i].value == 1){
					elem1.style.display = "";
					elem2.style.display = "none";
				}else {
					elem1.style.display = "none";
					elem2.style.display = "";
				}
			}
		}
	} else {
		if (document.JJ901SOLR001ActionForm.solrRequest.checked) {
			if(document.JJ901SOLR001ActionForm.solrRequest.value == 1){
				elem1.style.display = "";
				elem2.style.display = "none";
			}else {
				elem1.style.display = "none";
				elem2.style.display = "";
			}
		}
	}
}
</script>
</head>

<body onload="view();">
<h2>Elasticsearch取得</h2>
<a href="http://wwwtst.suumo.jp/wiki/index.php?cmd=read&page=%E3%83%81%E3%83%BC%E3%83%A0%2FCBK%2F%E3%82%A4%E3%83%B3%E3%83%95%E3%83%A9">Elasticsearch関連資料</a><br/>
<r2:form method="POST">
<r2:radio property="solrRequest" value="1" onclick="view();"/>クエリを作成
<r2:radio property="solrRequest" value="2" onclick="view();"/>パラメータを直接入力
<br/>
<br/>
検品を選択してください<br/>
<r2:select property="side1">
	<r2:option value="es_1">第1検品</r2:option>
	<r2:option value="es_2">第2検品</r2:option>
	<r2:option value="es_3">第3検品</r2:option>
	<r2:option value="es_4">第4検品</r2:option>
	<r2:option value="es_5">第5検品</r2:option>
	<r2:option value="es_6">第6検品</r2:option>
	<r2:option value="es_7">第7検品</r2:option>
	<r2:option value="es_8">第8検品</r2:option>
	<r2:option value="es_9">第9検品</r2:option>
</r2:select><br/>
インデックスを選択してください<br/>
<r2:select property="side2">
	<r2:option value="seach_all">fr0001,fr0002,cm0001_fr</r2:option>
	<r2:option value="seach_fr">fr0001,fr0002</r2:option>
	<r2:option value="seach_fr0001">fr0001</r2:option>
	<r2:option value="seach_fr0002">fr0002</r2:option>
	<r2:option value="cm0001">cm0001</r2:option>
	<r2:option value="cm0002">cm0002</r2:option>
</r2:select><br/>
ステータスを選択してください<br/>
<r2:select property="side3">
	<r2:option value="active">アクティブ</r2:option>
	<r2:option value="standby">スタンバイ</r2:option>
</r2:select>
<br/>
<br/>
<div id="area1">
各パラメータを入力してください（注意：セパレータ：Elasticsearch→"__"）<br/>
q:<br/>
<r2:textarea property="query" rows="5" cols="100"/><br/>
<br/>
sort:<br/>
<r2:text property="sort" size="100"  maxlength="300"/><br/>
<br/>
start,rows:<br/>
（注意：Elasticsearch時、start+rows > 99999 の場合はエラーとなります。）<br/>
<r2:text property="start" size="5" value="0"/>　<r2:text property="rows" size="5" value="10"/><br/>
<br/>
fl:<br/>
<r2:text property="field" size="100"  maxlength="300"/><br/>
<br/>
facet.field:<br/>
<r2:text property="facetField" size="100"  maxlength="300"/><br/>
<br/>
group.field：<br/>
<r2:text property="groupField" size="100"  maxlength="300"/><br/>
<br/>
</div>

<div id="area2">
Solr/Elasticsearchへのパラメータを入力してください<br/>
（注意：セパレータ：Elasticsearch→"__"）<br/>
<br/>
<r2:textarea property="solrParam" rows="10" cols="100"/><br/>
</div>

<br/>
<r2:submit property="index" value="検索"/><br/>
<br/>
${err}
<br/>
</r2:form>
</body>
</html>