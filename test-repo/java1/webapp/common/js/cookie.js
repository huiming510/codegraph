//更新submit押下時に確認ダイアログ表示
$('.js-update').click(function(){
    if(!confirm('Cookieを更新しますか')){
        return false;
    }else{
        return true;
    }
});