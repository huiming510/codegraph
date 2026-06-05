<%@ page import="r2framework.web.util.R2ActionMessagesUtil"%>
<%@ page import="jp.co.rct.jj.base.codetable.CodeGroup"%>
<%@ page import="jp.co.rct.jj.base.codetable.CodeTableCache"%>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ja" lang="ja">
<head>
<meta http-equiv="content-style-type" content="text/css" />
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<title>掲載確定の処理時間見立てツール</title>
<jj:css rel="stylesheet" href="${f:url('/common/css/animate.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/common.css')}" />
<jj:css rel="stylesheet" href="${f:url('/common/css/index.css')}" />
<style>
textarea {
	width: auto;
}

th {
	font-weight: normal;
	text-align: left;
	padding-right: 20px;
}

a {
	margin: 5px;
}

.dispMessage {
	font-size: x-large;
	color: red;
}

.infomation {
	margin: 15px 0px;
}

.bukkenSu {
	display: inline;
}

.IFjikan {
	padding-left: 40px;
	display: inline;
}

.estimate001-container {
	padding-bottom: 20px;
	margin-right: auto;
	margin-left: auto;
}

.outputarea {
	padding-bottom: 100px;
}

.submitButton {
	margin-left: 40px;
}
</style>
</head>
<body>
	<r2:form styleId="contact_form" action="estimatedProcessingTime" method="POST">
		<div class="header">
			<div class="container row">
				<div class="col-md-8">
					<h2 class="balloon fadeInUp animated">掲載確定の処理時間見立てツール</h2>
				</div>
				<div class="col-md-4 suumo01">
					<img class="lightSpeedIn animated" src="/unyo-tool/common/img/suumo_01.png">
				</div>
			</div>
		</div>
		<div class="container">
			<div class="dispMessage">
				<r2:write name="resultJudgmentMessage" spacefilter="false" />
			</div>
			<div class="infomation">
				<div class="bukkenSu">
					物件数 ：
					<r2:text property="bukkenSu" value="${bukkenSu}" />
					<r2:hidden property="bukkenSu" value="${bukkenSu}" />
				</div>
				<div class="IFjikan">
					IF到着時間 ： <select name="arrivalTime"><option value="${arrivalTime}" selected="selected">${displayTime}</option>
						<option value="0">0:00</option>
						<option value="10">0:10</option>
						<option value="20">0:20</option>
						<option value="30">0:30</option>
						<option value="40">0:40</option>
						<option value="50">0:50</option>
						<option value="60">1:00</option>
						<option value="70">1:10</option>
						<option value="80">1:20</option>
						<option value="90">1:30</option>
						<option value="100">1:40</option>
						<option value="110">1:50</option>
						<option value="120">2:00</option>
						<option value="130">2:10</option>
						<option value="140">2:20</option>
						<option value="150">2:30</option>
						<option value="160">2:40</option>
						<option value="170">2:50</option>
						<option value="180">3:00</option>
						<option value="190">3:10</option>
						<option value="200">3:20</option>
						<option value="210">3:30</option>
						<option value="220">3:40</option>
						<option value="230">3:50</option>
						<option value="240">4:00</option>
						<option value="250">4:10</option>
						<option value="260">4:20</option>
						<option value="270">4:30</option>
						<option value="280">4:40</option>
						<option value="290">4:50</option>
						<option value="300">5:00</option>
						<option value="310">5:10</option>
						<option value="320">5:20</option>
						<option value="330">5:30</option>
						<option value="340">5:40</option>
						<option value="350">5:50</option>
						<option value="360">6:00</option>
						<option value="370">6:10</option>
						<option value="380">6:20</option>
						<option value="390">6:30</option>
						<option value="400">6:40</option>
						<option value="410">6:50</option>
						<option value="420">7:00</option>
						<option value="430">7:10</option>
						<option value="440">7:20</option>
						<option value="450">7:30</option>
						<option value="460">7:40</option>
						<option value="470">7:50</option>
						<option value="480">8:00</option>
						<option value="490">8:10</option>
						<option value="500">8:20</option>
						<option value="510">8:30</option>
						<option value="520">8:40</option>
						<option value="530">8:50</option>
						<option value="540">9:00</option>
						<option value="550">9:10</option>
						<option value="560">9:20</option>
						<option value="570">9:30</option>
						<option value="580">9:40</option>
						<option value="590">9:50</option>
						<option value="600">10:00</option>
						<option value="610">10:10</option>
						<option value="620">10:20</option>
						<option value="630">10:30</option>
						<option value="640">10:40</option>
						<option value="650">10:50</option>
						<option value="660">11:00</option>
						<option value="670">11:10</option>
						<option value="680">11:20</option>
						<option value="690">11:30</option>
						<option value="700">11:40</option>
						<option value="710">11:50</option>
						<option value="720">12:00</option>
						<option value="730">12:10</option>
						<option value="740">12:20</option>
						<option value="750">12:30</option>
						<option value="760">12:40</option>
						<option value="770">12:50</option>
						<option value="780">13:00</option>
						<option value="790">13:10</option>
						<option value="800">13:20</option>
						<option value="810">13:30</option>
						<option value="820">13:40</option>
						<option value="830">13:50</option>
						<option value="840">14:00</option>
						<option value="850">14:10</option>
						<option value="860">14:20</option>
						<option value="870">14:30</option>
						<option value="880">14:40</option>
						<option value="890">14:50</option>
						<option value="900">15:00</option>
						<option value="910">15:10</option>
						<option value="920">15:20</option>
						<option value="930">15:30</option>
						<option value="940">15:40</option>
						<option value="950">15:50</option>
						<option value="960">16:00</option>
						<option value="970">16:10</option>
						<option value="980">16:20</option>
						<option value="990">16:30</option>
						<option value="1000">16:40</option>
						<option value="1010">16:50</option>
						<option value="1020">17:00</option>
						<option value="1030">17:10</option>
						<option value="1040">17:20</option>
						<option value="1050">17:30</option>
						<option value="1060">17:40</option>
						<option value="1070">17:50</option>
						<option value="1080">18:00</option>
						<option value="1090">18:10</option>
						<option value="1100">18:20</option>
						<option value="1110">18:30</option>
						<option value="1120">18:40</option>
						<option value="1130">18:50</option>
						<option value="1140">19:00</option>
						<option value="1150">19:10</option>
						<option value="1160">19:20</option>
						<option value="1170">19:30</option>
						<option value="1180">19:40</option>
						<option value="1190">19:50</option>
						<option value="1200">20:00</option>
						<option value="1210">20:10</option>
						<option value="1220">20:20</option>
						<option value="1230">20:30</option>
						<option value="1240">20:40</option>
						<option value="1250">20:50</option>
						<option value="1260">21:00</option>
						<option value="1270">21:10</option>
						<option value="1280">21:20</option>
						<option value="1290">21:30</option>
						<option value="1300">21:40</option>
						<option value="1310">21:50</option>
						<option value="1320">22:00</option>
						<option value="1330">22:10</option>
						<option value="1340">22:20</option>
						<option value="1350">22:30</option>
						<option value="1360">22:40</option>
						<option value="1370">22:50</option>
						<option value="1380">23:00</option>
						<option value="1390">23:10</option>
						<option value="1400">23:20</option>
						<option value="1410">23:30</option>
						<option value="1420">23:40</option>
						<option value="1430">23:50</option></select>
				</div>
			</div>
			<div class="estimate001-container">
				<r2:define id="URL" value="http://wwwunyotool.suumo.jp.suu.raftel/nri_unyo/jp1-job-search/job-search.cgi" />
				<%-- できたらやる：検索期間は当日から一か月前まで --%>
				<r2:define id="startDate" value="SDATE=${f:u(startDate)}&SDATE_T=00%3A00%3A00" />
				<r2:define id="endDate" value="EDATE=${f:u(endDate)}&EDATE_T=23%3A59%3A59" />
				<r2:define id="etcParam" value="STIME=00%3A00%3A00&ETIMET=23%3A59%3A59&RSTIME=0&RETIME=16666&SPAN=&RESEARCH=checked" />
				<%-- ES反映ジョブ名 --%>
				<r2:define id="esJobNameYakan" value="%2FSUU%2FADMXJJ%2FG_HONBAN_2%2FA3ZG0001%2FTZ9999_FR%2FTRG_SLRCASHCLR_FR" />
				<r2:define id="esJobName11" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0001%2FFBSLR00660" />
				<r2:define id="esJobName15" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0002%2FFBSLR00660" />
				<r2:define id="esJobName19" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0003%2FFBSLR00660" />
				ES反映完了時間：
				<a href="${URL}?NAME=${esJobNameYakan}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">夜間便</a>
				<a href="${URL}?NAME=${esJobName11}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">11時便</a>
				<a href="${URL}?NAME=${esJobName15}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">15時便</a>
				<a href="${URL}?NAME=${esJobName19}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">19時便</a>
				<br />
				<r2:textarea property="esJisseki" value="${esJisseki}" rows="15" cols="100" />
			</div>
			<div class="estimate001-container">
				<%-- DB反映ジョブ名 --%>
				<r2:define id="dbJobNameYakan" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5%25G0002%2FTT0001%2FFBFFR01070_01" />
				<r2:define id="dbJobName11" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0001%2FTRG_FFR_UPDATE" />
				<r2:define id="dbJobName15" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0002%2FTRG_FFR_UPDATE_2" />
				<r2:define id="dbJobName19" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0003%2FTRG_FFR_UPDATE_3" />
				DB反映完了時間：
				<a href="${URL}?NAME=${dbJobNameYakan}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">夜間便</a>
				<a href="${URL}?NAME=${dbJobName11}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">11時便</a>
				<a href="${URL}?NAME=${dbJobName15}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">15時便</a>
				<a href="${URL}?NAME=${dbJobName19}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">19時便</a>
				<br />
				<r2:textarea property="dbJisseki" value="${dbJisseki}" rows="15" cols="100" />
			</div>
			<div class="estimate001-container">
				<%-- 掲載確定完了ジョブ名 --%>
				<r2:define id="keisaikakuteiNameYakan" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5%25G0002%2FTT0001" />
				<r2:define id="keisaikakuteiName11" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0001" />
				<r2:define id="keisaikakuteiName15" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0002" />
				<r2:define id="keisaikakuteiName19" value="%2FSUU%2FADMXJJ%2FG_HONBAN_3%2FA5ZG0001%2FTT0003" />
				掲載確定処理全体の完了時間：
				<a href="${URL}?NAME=${keisaikakuteiNameYakan}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">夜間便</a>
				<a href="${URL}?NAME=${keisaikakuteiName11}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">11時便</a>
				<a href="${URL}?NAME=${keisaikakuteiName15}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">15時便</a>
				<a href="${URL}?NAME=${keisaikakuteiName19}&MAST_CHK=checked&CMNT=%25&${startDate}&${endDate}&${etcParam}" target="_blank">19時便</a>
				<br />
				<r2:textarea property="keisaiJisseki" value="${keisaiJisseki}" rows="15" cols="100" />
			</div>
			<div class="estimate001-container">
				物件数：
				<a href="http://wwwadm.fn.forrent.jp.suu.raftel/unyou/suumo_if_count/suumo_if_count.html" target="_blank">実績取得ツール</a>
				</br>
				<r2:textarea property="jissekiBukkenSu" value="${jissekiBukkenSu}" rows="15" cols="100" />
				<r2:submit property="result" value="算出" styleClass="submitButton" />
			</div>
		</div>
		</div>
	</r2:form>
	<div class="container outputarea">
		<table border="0">
			<tr>
				<th>ES反映完了時刻</th>
				<td>
					<r2:write name="esProcessCompleteTime" spacefilter="false" />
				</td>
			</tr>
			<tr>
				<th>DB反映完了時刻</th>
				<td>
					<r2:write name="dbProcessCompleteTime" spacefilter="false" />
				</td>
			</tr>
			<tr>
				<th>掲載確定処理全体の完了時刻</th>
				<td>
					<r2:write name="keisaiProcessCompleteTime" spacefilter="false" />
				</td>
			</tr>
		</table>
	</div>
</body>
</html>