<!DOCTYPE HTML>
<html lang="ja">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta http-equiv="Content-Script-Type" content="text/javascript">
<meta http-equiv="Content-Style-Type" content="text/css">
<jj:css rel="stylesheet" type="text/css" href="/unyo-tool/common/css/abtest.css"/>

<title>ABテスト切り替えツール</title>

</head>

<body>
	<h1>${envName}検品　ABテスト比率切り替えツール</h1>
	<r2:write name="executeMessage" />
	<div class = "how-to-use">
		<h3>利用方法を見る場合、<span class = "accordion">こちら</span>をクリック</h3>
		<div class="js-how-to-use" style="display: none;">
			<h4>■比率変更</h4>
			<div class="order">
				 1.対象テストIDのバージョンを現在から+1する<br>
				 2.比率を変更する<br>
					<span class="detail">比率は1～4で合計100になるよう設定してください。<br></span>
				 3.対象テストID行の「変更」ボタンを押す<br>
			</div>

			<h4> ■削除</h4>
			<div class="order">
				1.対象テストID行の「削除」ボタンを押す<br>
			</div>

			<h4>■新規追加</h4>
			<div class="order">
				1.画面最下部の新規追加行の必要項目を埋める<br>
				<span class="detail">以下注意点<br></span>
				<div class="attention">
					・比率とパターンIDはセットで入力してください。<br>
					・最低2つはパターンIDと比率のセットが必要です。<br>
				</div>
				2.新規追加行の「新規登録」ボタンを押す<br>
			</div>
		</div>
	</div>
	<h3><a href = "https://confluence.sprocket3.systems/pages/viewpage.action?pageId=130800224">各IDの管理資料はこちら</a></h3>
	<h3>こちらは更新画面です。更新しない場合は<a href="/unyo-tool/JJ901ABTEST002/">こちら</a></h3>
	<h2>■比率変更</h2>
	<table>
		<thead>
			<tr>
				<th>テストID</th>
				<th>バージョン</th>
				<th>パターンID1</th>
				<th>比率1</th>
				<th>パターンID2</th>
				<th>比率2</th>
				<th>パターンID3</th>
				<th>比率3</th>
				<th>パターンID4</th>
				<th>比率4</th>
				<th>更新実行</th>
			</tr>
		</thead>
		<tbody>
			<r2logic:iterate name="abTestIdList" id="abTest" indexId="testListIndex">
				<r2:form styleId="js-form" action="update" method="post" >
					<tr>
						<td class ="testId">
							<r2:write name="abTest" property="testId" />
							<r2:hidden name="abTest" property="testId" />
							<r2:hidden property="fileDate" value="${f:h(fileDate)}"/>
						</td>
						<td class="version">
							<r2:text name="abTest" property="version" styleClass="textbox" value="${abTest.version}" />
						</td>
						<r2logic:iterate id="testCase" name="abTest" property="caseList" indexId="caseIndex">
								<td class ="patternId">
									<r2:write name="testCase" property="patternId"  />
									<r2:hidden name="testCase" property="patternId${caseIndex}" value="${testCase.patternId}" />
								</td>
								<td class="ratio">
									<r2:text name="testCase" property="ratio${caseIndex}" styleClass="textbox" value="${testCase.ratio}"  />
								</td>
						</r2logic:iterate>
						<td><input type="submit" name="hoge" class="js-update" value="変更"/></td>
					</tr>
				</r2:form>
			</r2logic:iterate>
		</tbody>
	</table>
	<br/>
	<h2>■削除</h2>
	<table>
		<thead>
			<tr>
				<th>テストID</th>
				<th>削除実行</th>
			</tr>
		</thead>
		<tbody>
			<r2logic:iterate name="abTestIdList" id="abTest" indexId="testListIndex">
				<r2:form styleId="js-form" action="delete" method="post" >
					<tr>
						<td class ="testId">
							<r2:write name="abTest" property="testId" />
							<r2:hidden name="abTest" property="testId" />
							<r2:hidden property="fileDate" value="${f:h(fileDate)}"/>
						</td>
						<td><input type="submit" name="hoge" class="js-delete" value="削除"/></td>
					</tr>
				</r2:form>
			</r2logic:iterate>
		</tbody>
	</table>
	<br/>
	<h2>■新規追加</h2>
	<table>
		<thead>
			<tr>
				<th>テストID</th>
				<th>バージョン</th>
				<th>パターンID1</th>
				<th>比率1</th>
				<th>パターンID2</th>
				<th>比率2</th>
				<th>パターンID3</th>
				<th>比率3</th>
				<th>パターンID4</th>
				<th>比率4</th>
				<th>追加実行</th>
			</tr>
		</thead>
		<tbody>
			<r2:form styleId="js-form" action="add" method="post" >
				<tr>
					<td class ="testId">
						<r2:text property="testId" />
						<r2:hidden property="fileDate" value="${f:h(fileDate)}"/>
					</td>
					<td class="version">
						<r2:text property="version" styleClass="textbox" />
					</td>
					<td class ="patternId">
						<r2:text property="patternId0" />
					</td>
					<td class="ratio">
						<r2:text property="ratio0" styleClass="textbox" />
					</td>
					<td class ="patternId">
						<r2:text property="patternId1" />
					</td>
					<td class="ratio">
						<r2:text property="ratio1" styleClass="textbox" />
					</td>
					<td class ="patternId">
						<r2:text property="patternId2" />
					</td>
					<td class="ratio">
						<r2:text property="ratio2" styleClass="textbox" />
					</td>
					<td class ="patternId">
						<r2:text property="patternId3" />
					</td>
					<td class="ratio">
						<r2:text property="ratio3" styleClass="textbox" />
					</td>
					<td>
						<input type="submit" name="hoge" class="js-add" value="追加">
					</td>
				</tr>
			</r2:form>
		</tbody>
	</table>
	<jj:script src="${f:url('/common/js/jquery-3.2.1.min.js')}" />
	<jj:script src="${f:url('/common/js/abtest.js')}" />
</body>
</html>
