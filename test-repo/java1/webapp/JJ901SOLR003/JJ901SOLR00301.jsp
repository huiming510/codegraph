<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<title>Elasticsearch検索インデックス判定</title>
<jj:css rel="stylesheet" href="${f:url('/common/css/animate.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/common.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/index.css')}" />
</head>
<body>
	<div class="header">
		<div class="container">
			<div class="row">
				<div class="col-md-8">
					<h2 class="balloon fadeInUp animated">Elasticsearch検索インデックス判定</h2>
				</div>
				<div class="col-md-4 suumo01">
					<img class="lightSpeedIn animated" src="../common/img/suumo_01.png">
				</div>
			</div>
		</div>
	</div>
	<br />
Elasticsearchへのクエリを入力してください<br/>
（注意１：セパレータ：Elasticsearch→"__"）<br/>
（注意２：デバックプリントで出力されている”q_”系パラメータは削除してください。エラーが発生します。）<br/>
参考資料【Elasticsearch】インデックスの考え方.ppt（156760245）<br/>
	<r2:form method="POST">
		<br/>
		<r2:textarea property="solrQuery" rows="10" cols="100"/><br/>
		<br/>
		<r2:submit property="index" value="submit"/><br/>
		<br/>
		${target}
		<br/>
	</r2:form>
</body>
</html>