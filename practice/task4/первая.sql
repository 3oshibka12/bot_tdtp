-- LOST UPDATE
rollback

begin;
update score set scor = scor - 300 where userid=1;
-- ...
commit


-- NON-REPETAABLE READ

begin;
select scor from score where userid = 1
-- ...
select scor from score where userid = 1 
commit


-- PHANTOM READ

begin;
select count(*) from score
-- ...
select count(*) from score
commit


-- DIRTY READ

start transaction;
set transaction isolation level read uncommitted;
select scor from score where userid = 1
-- ...
select scor from score where userid = 1 
rollback