%~d0
cd %~p0


:: If you want to keep the Command Prompt Window,you can use 'cmd /k' option.
:: If you want to close the Commond Prompt Window,you can comment out the bellow.
cmd /k mvn -e pre-clean antrun:run eclipse:clean eclipse:eclipse -DdownloadSources=true  dependency:copy-dependencies

:: If you want to close the Commond Prompt Window,you can execute the bellow.
:: mvn -e pre-clean antrun:run eclipse:clean eclipse:eclipse -DdownloadSources=true   dependency:copy-dependencies > maven_execute_last.log

