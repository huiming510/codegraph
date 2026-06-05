//更新submit押下時に確認ダイアログ表示
$('.js-update').click(function(){
    if(!confirm('yamlファイルを更新しますか')){
        return false;
    }else{
        return true;
    }
});

//削除submit押下時に確認ダイアログ表示
$('.js-delete').click(function(){
    if(!confirm('テストIDを削除しますか')){
        return false;
    }else{
        return true;
    }
});

//新規追加submit押下時に確認ダイアログ表示
$('.js-add').click(function(){
    if(!confirm('テストIDを新規追加しますか')){
        return false;
    }else{
        return true;
    }
});

//利用方法がクリックされたら要素を表示する
$(function(){
    $('.accordion').click(function(){
        $('.js-how-to-use').slideToggle();
    });
});