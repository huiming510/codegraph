<html lang="ja">
	<head>
		<title>デバッグプリント設定</title>
		<meta http-equiv="content-type" content="text/html; charset=utf-8" />
		<meta http-equiv="content-style-type" content="text/css" />
		<meta http-equiv="content-script-type" content="text/javascript" />
		<jj:css rel="stylesheet" type="text/css" href="${f:url('/common/css/bootstrap.min.css')}" />
		<jj:css rel="stylesheet" type="text/css" href="${f:url('/common/css/font-awesome.min.css')}" />
	</head>

	<body>
		<header>
			<div class="row">
				<h1 class="bg-dark text-white rounded col-md-12 p-2 m-0 text-center">デバッグプリント設定</h1>
			</div>
		</header>
		<div class="container-fluid bg-light">
			<div class="row p-2 justify-content-center">
				<% Boolean isDebugPrint = (Boolean)request.getAttribute("isDebugPrint"); %>
				<% if(isDebugPrint) { %>
					<div class="rounded text-success text-center p-3" style="font-size:6em;">
						<span class="border-1 font-weight-bold">出力あり</span><br />
						<span class="fa fa-check-circle"></span>
					</div>
				<% } else { %>
					<div class="rounded text-danger text-center p-3" style="font-size:6em;">
						<span class="border-1 font-weight-bold">出力なし</span><br />
						<span class="fa fa-minus-circle"></span>
					</div>
				<% } %>
			</div>
			<div class="row justify-content-center">
				<r2:form method="post" action="execteSetting">
					<% if(isDebugPrint) { %>
						<input type="hidden" name="isDebugPrint" value="false" />
						<button class="btn btn-outline-success" disabled>
							<span class="fa fa-toggle-on fa-2x pr-1"></span><span class="font-weight-bold h3">O N</span>
						</button>
						<button type="submit" class="btn btn-outline-danger">
							<span class="fa fa-toggle-off fa-2x pr-1"></span><span class="font-weight-bold h3">OFF</span>
						</button>
					<% } else { %>
						<input type="hidden" name="isDebugPrint" value="true" />
						<button type="submit" class="btn btn-outline-success">
							<span class="fa fa-toggle-on fa-2x pr-1"></span><span class="font-weight-bold h3">O N</span>
						</button>
						<button class="btn btn-outline-danger" disabled>
							<span class="fa fa-toggle-off fa-2x pr-1"></span><span class="font-weight-bold h3">OFF</span>
						</button>
					<% } %>
				</r2:form>
			</div>
		</div>
		<footer>
			<div class="row bg-dark rounded col-md-12 p-2 m-0 text-center">
				<a class="text-white" href="/unyo-tool/"><span class="fa fa-home fa-3x pr-1"></span></a>
			</div>
		</footer>
	</body>
</html>
