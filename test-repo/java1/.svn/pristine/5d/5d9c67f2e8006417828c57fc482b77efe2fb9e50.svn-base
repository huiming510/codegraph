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
	<h3>こちらは参照画面です。更新したい場合は<a href="/unyo-tool/JJ901ABTEST001/">こちら</a></h3>
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
			</tr>
		</thead>
		<tbody>
			<r2logic:iterate name="abTestIdList" id="abTest" indexId="testListIndex">
				<r2:form>
					<tr>
						<td class ="testId">
							<r2:write name="abTest" property="testId" />
						</td>
						<td class="version">
							<r2:write name="abTest" property="version" />
						</td>
						<r2logic:iterate id="testCase" name="abTest" property="caseList" indexId="caseIndex">
							<td class ="patternId">
								<r2:write name="testCase" property="patternId" />
							</td>
							<td class="ratio">
								<r2:write name="testCase" property="ratio" />
							</td>
						</r2logic:iterate>
					</tr>
				</r2:form>
			</r2logic:iterate>
		</tbody>
	</table>
</body>
</html>