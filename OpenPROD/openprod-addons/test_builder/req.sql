insert into ir_translation (lang, src, name, type, res_id, value, user_id)
select 'te_IN', src, name, type, res_id, lower(concat(value, '$', substring(md5(concat(src, type, name, res_id)) for 4), '$')), user_id
from ir_translation
where lang = 'fr_FR';
