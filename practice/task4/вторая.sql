-- LOST UPDATE

-- rollback 
-- select * from score

begin;
update score set scor = scor + 300 where userid=1 --ждет завершения первой
commit -- изменила старые данные


-- NON-REPETAABLE READ

begin;
update score set scor = scor + 300 where userid=1
commit


-- PHANTOM READ
begin;
insert into score values (2, 1000);
commit


-- DIRTY READ
start transaction;
set transaction isolation level read uncommitted;
update score set scor = scor + 300 where userid=1;
-- ...
rollback