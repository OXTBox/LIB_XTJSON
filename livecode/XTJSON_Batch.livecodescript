script "XTJSON_Batch"
######################################################################################
## XTJSON BATCH  (13 11 2026)
## One click: every stack waiting in ~/projects/LIB_LLMIN/LIB_XTJSON (any depth) is taken
## apart into XTJSON by LCHarvest2, one after another, and then moved out of the inbox:
##   harvest   -> ~/projects/XTJSON/batch/<same relative path, without extension>/
##   original  -> ~/projects/LIB_LLMOUT/Read/LIB_XTJSON/<same relative path>
## Failures stay in the inbox. Every step is written to XTJSON/batch/_batch_log.tsv
## (START before a stack, OK or FAIL after it). A stack that STARTed and never finished
## crashed the engine: it is marked CRASHED and skipped on the next run, so one bad stack
## can't stop the batch.
## Open this file in LiveCode (IDE or the LIB_MCP standalone): the window builds itself.
##   Run   scan the inbox and harvest everything still waiting (the one click); at the end
##         the stacks that crashed are retried once by themselves, custom data sampled
##   Retry crashed   the same retry, by hand (also for stacks retried before)
## Stacks over 2 MB are harvested with their custom property DATA sampled (first 5 entries
## of each array, first 5 lines of each long text; LCHarvest2 option customSample).
##   Scan  just list what is waiting      Stop  finish the current stack, then stop
## From a script:  Batch.Run  /  Batch.Scan  /  Batch.Stop  /  Batch.Report()
## The stacks' own handlers never run (messages are locked while they are loaded).
######################################################################################

constant kHarvestLib = "XT_HarvestLib"
constant kStackExt = "livecode,rev,mc,lc"
constant kBigStack = 2097152   -- stacks over 2 MB: custom property DATA is sampled (first 5 entries)
constant kSample = 5

local sPaths        -- [projects|inbox|out|done|harvester|log]
local sList         -- the stacks found: relative paths, one per line
local sState        -- [rel] -> waiting / OK / FAIL / CRASHED / moved
local sSize         -- [rel] -> bytes (from the folder listing)
local sStop, sRunning, sIndex, sStarted, sDone, sFailed
local sTried        -- [rel] true once STARTed in this run: never twice (a loop guard)
local sForceSample  -- [rel] true: sample its custom data whatever its size (Retry crashed)
local sRetried      -- [rel] true: the log already shows a RETRY for it (never auto-retried twice)

-------------------------------------------------------------------- the window

-- only for this window: a harvested stack opening must never rebuild or rescan (that reset
-- the states mid-run once and the batch looped on a stack it had already moved)
on preOpenStack
   if not (the long id of the target contains the long id of me) then pass preOpenStack   -- the target is this stack's card
   Batch.Paths
   Batch.BuildUI
   if not sRunning then Batch.Scan
end preOpenStack

on Batch.BuildUI
   lock screen
   set the title of me to "XTJSON Batch: stacks in the inbox -> XTJSON"
   set the rect of me to 100, 100, 1000, 720
   if there is not a field "Info" then
      reset the templateField
      create field "Info"
      set the rect of field "Info" to 10, 10, 890, 70
      set the lockText of field "Info" to true
      set the opaque of field "Info" to false
      set the showBorder of field "Info" to false
   end if
   put "Inbox:" && sPaths["inbox"] & cr & "Harvests:" && sPaths["out"] & cr & "Done:" && sPaths["done"] into field "Info"
   Batch.Button "Run", 10, 76, "Batch.Run"
   Batch.Button "Scan", 120, 76, "Batch.Scan"
   Batch.Button "Stop", 230, 76, "Batch.Stop"
   Batch.Button "Retry crashed", 780, 76, "Batch.RetryCrashed"
   if there is not a field "Status" then
      reset the templateField
      create field "Status"
      set the rect of field "Status" to 340, 76, 770, 100
      set the lockText of field "Status" to true
      set the showBorder of field "Status" to false
      set the opaque of field "Status" to false
   end if
   if there is not a field "List" then
      reset the templateField
      create field "List"
      set the rect of field "List" to 10, 108, 890, 610
      set the listBehavior of field "List" to true
      set the lockText of field "List" to true
      set the vScrollbar of field "List" to true
      set the tabStops of field "List" to "90,190"
      set the textFont of field "List" to "Courier New"
      set the textSize of field "List" to 11
   end if
   unlock screen
end Batch.BuildUI

on Batch.Button pName, pLeft, pTop, pMsg
   if there is not a button pName then
      reset the templateButton
      create button pName
      set the rect of button pName to pLeft, pTop, pLeft + 100, pTop + 26
      set the script of button pName to "on mouseUp" & cr & "   " & pMsg & cr & "end mouseUp"
   end if
end Batch.Button

on Batch.Say pText
   if there is a field "Status" then put pText into field "Status"
end Batch.Say

on Batch.ShowList
   local tOut, tRel
   if there is not a field "List" then exit Batch.ShowList
   repeat for each line tRel in sList
      put sState[tRel] & tab & Batch.SizeText(tRel) & tab & tRel & cr after tOut
   end repeat
   put tOut into field "List"
end Batch.ShowList

-------------------------------------------------------------------- paths

-- everything relative to ~/projects, found from this file: <projects>/LIB_XTJSON/livecode/XTJSON_Batch.livecodescript
on Batch.Paths
   local tPath
   put the effective filename of me into tPath
   replace "\" with "/" in tPath          -- opened as a Windows path (backslashes): LiveCode wants /
   set the itemDel to "/"
   put item 1 to -4 of tPath into sPaths["projects"]
   put sPaths["projects"] & "/LIB_LLMIN/LIB_XTJSON" into sPaths["inbox"]
   put sPaths["projects"] & "/XTJSON/batch" into sPaths["out"]
   put sPaths["projects"] & "/LIB_LLMOUT/Read/LIB_XTJSON" into sPaths["done"]
   put sPaths["projects"] & "/LIB_XTJSON/livecode/LCHarvest2.livecodescript" into sPaths["harvester"]
   put sPaths["out"] & "/_batch_log.tsv" into sPaths["log"]
end Batch.Paths

function Batch.SizeText pRel
   local tSize
   put sSize[pRel] into tSize
   if tSize is not a number then return "-"
   if tSize > 1048576 then return round(tSize / 1048576, 1) & " MB"
   return round(tSize / 1024) & " KB"
end Batch.SizeText

-------------------------------------------------------------------- scanning

on Batch.Scan
   local tLog, tLine, tRel
   if sRunning then return sList        -- never rescan under a running batch
   if sPaths["inbox"] is empty then Batch.Paths
   put empty into sList
   put empty into sSize
   Batch.ScanFolder sPaths["inbox"], empty
   -- what the log says about each stack (the last word wins; START alone = it crashed)
   put empty into sState
   put empty into sRetried
   if there is a file sPaths["log"] then put URL ("file:" & sPaths["log"]) into tLog
   set the itemDel to tab
   repeat for each line tLine in tLog
      put item 3 of tLine into tRel
      if tRel is empty then next repeat
      switch item 2 of tLine
         case "START"
            put "CRASHED" into sState[tRel]
            break
         case "RETRY"
            put true into sRetried[tRel]
            break
         case "OK"
         case "FAIL"
         case "GONE"
            put item 2 of tLine into sState[tRel]
            break
      end switch
   end repeat
   set the itemDel to comma
   repeat for each line tRel in sList
      if sState[tRel] is empty then put "waiting" into sState[tRel]
      if sState[tRel] is "OK" then put "MOVEFAIL" into sState[tRel]   -- harvested, but still here
   end repeat
   Batch.ShowList
   Batch.Say (the number of lines of sList) && "stacks in the inbox;" && Batch.Count("waiting") && "waiting," && \
         Batch.Count("FAIL") && "failed before," && Batch.Count("CRASHED") && "crashed before"
   return sList
end Batch.Scan

on Batch.ScanFolder pFolder, pRel
   local tLine, tF, tSub, tSuffix
   repeat for each line tLine in files(pFolder, "detailed")
      set the itemDel to comma
      put urlDecode(item 1 of tLine) into tF
      if tF contains "Zone.Identifier" or "." is not in tF then next repeat
      set the itemDel to "."
      put toLower(item -1 of tF) into tSuffix
      set the itemDel to comma
      if tSuffix is among the items of kStackExt then
         put pRel & tF & cr after sList
         put item 2 of tLine into sSize[pRel & tF]
      end if
   end repeat
   repeat for each line tSub in folders(pFolder)
      if tSub is "." or tSub is ".." then next repeat
      Batch.ScanFolder pFolder & "/" & tSub, pRel & tSub & "/"
   end repeat
   if pRel is empty and char -1 of sList is cr then delete char -1 of sList
end Batch.ScanFolder

function Batch.Count pState
   local tRel, n
   put 0 into n
   repeat for each line tRel in sList
      if sState[tRel] is pState then add 1 to n
   end repeat
   return n
end Batch.Count

-------------------------------------------------------------------- the run

-- the one click: scan, then one stack at a time (sent, so the window stays alive)
on Batch.Run
   if sRunning then exit Batch.Run
   Batch.Scan
   put empty into sTried
   put false into sStop
   put true into sRunning
   put 0 into sDone
   put 0 into sFailed
   put the seconds into sStarted
   Batch.MakeFolders sPaths["out"]
   Batch.MakeFolders sPaths["done"]
   send "Batch.Next" to me in 100 milliseconds
end Batch.Run

on Batch.Stop
   put true into sStop
   Batch.Say "stopping after this stack..."
end Batch.Stop

on Batch.Next
   local tRel, tResult, tLine
   if sStop then
      put false into sRunning
      Batch.Say "stopped:" && sDone && "harvested," && sFailed && "failed. Run carries on from here."
      exit Batch.Next
   end if
   -- (never clear the variable of a repeat for each inside the loop: after the loop
   -- LiveCode leaves it holding the last line, and the batch re-picked that stack forever)
   put empty into tRel
   repeat for each line tLine in sList
      if sState[tLine] is "waiting" and sTried[tLine] is not true then
         put tLine into tRel
         exit repeat
      end if
   end repeat
   if tRel is empty then
      put false into sRunning
      -- once, by itself: the stacks that crashed, again with their custom data sampled
      Batch.Scan
      if Batch.AutoRetryCount() > 0 then
         Batch.Say "retrying" && Batch.AutoRetryCount() && "crashed stack(s) with sampled custom data..."
         Batch.RetryCrashed true
         exit Batch.Next
      end if
      Batch.Log "END", empty, sDone && "harvested," && sFailed && "failed in" && (the seconds - sStarted) && "s"
      Batch.Say "finished:" && sDone && "harvested," && sFailed && "failed (" & (the seconds - sStarted) & " s). Log:" && sPaths["log"]
      Batch.ShowList
      exit Batch.Next
   end if
   Batch.Say "harvesting" && tRel && "(" & (sDone + sFailed + 1) & " of" && (sDone + sFailed + Batch.Count("waiting")) & ")..."
   put true into sTried[tRel]
   Batch.Log "START", tRel, empty     -- written first: if the engine dies, the next run knows
   put Batch.HarvestOne(tRel) into tResult
   if line 1 of tResult begins with "harvested" then
      Batch.Log "OK", tRel, line 1 of tResult
      Batch.MoveDone tRel
      put "moved" into sState[tRel]
      add 1 to sDone
   else if tResult is "FAIL: file gone" then
      Batch.Log "GONE", tRel, empty
      put "GONE" into sState[tRel]
   else
      Batch.Log "FAIL", tRel, line 1 of tResult
      put "FAIL" into sState[tRel]
      add 1 to sFailed
   end if
   Batch.ShowList
   send "Batch.Next" to me in 50 milliseconds
end Batch.Next

-- one stack -> XTJSON (the same steps as LIB_XTJSON/python/xtjson_harvest.py)
function Batch.HarvestOne pRel
   local tSrc, tOut, tName, tResult, tErr, tOpt
   put sPaths["inbox"] & "/" & pRel into tSrc
   if there is not a file tSrc then return "FAIL: file gone"
   put sPaths["out"] & "/" & Batch.NoExt(pRel) into tOut
   Batch.MakeFolders tOut
   try
      if there is not a stack kHarvestLib then
         lock messages
         create invisible stack kHarvestLib
         unlock messages
         set the script of stack kHarvestLib to URL ("file:" & sPaths["harvester"])
         if the result is not empty then return "FAIL: LCHarvest2 does not compile:" && the result
      end if
      start using stack kHarvestLib
      lock messages
      put the short name of stack tSrc into tName
      unlock messages
      if tName is empty then return "FAIL: could not load"
      -- big stacks: their custom property DATA is sampled (first entries), see LCHarvest2
      put empty into tOpt
      if sSize[pRel] > kBigStack or sForceSample[pRel] is true then put kSample into tOpt["customSample"]
      harvestStack tName, tOut, tOpt
      put the result into tResult
      if tOpt["customSample"] > 0 then put " [custom data sampled: first" && kSample & "]" after line 1 of tResult
      lock messages
      if there is a stack tName then delete stack tName
      unlock messages
   catch tErr
      unlock messages
      return "FAIL:" && line 1 of tErr
   end try
   return tResult
end Batch.HarvestOne

-- the original leaves the inbox: LIB_LLMOUT/Read/LIB_XTJSON/<same relative path>
on Batch.MoveDone pRel
   local tTo
   put sPaths["done"] & "/" & pRel into tTo
   set the itemDel to "/"
   Batch.MakeFolders item 1 to -2 of tTo
   set the itemDel to comma
   if there is not a file (sPaths["inbox"] & "/" & pRel) then
      Batch.Log "MOVEFAIL", pRel, "not in the inbox any more"
      exit Batch.MoveDone
   end if
   -- never overwrite: a second file of that name gets a number
   if there is a file tTo then put Batch.FreeName(tTo) into tTo
   rename file (sPaths["inbox"] & "/" & pRel) to tTo
   if the result is not empty then Batch.Log "MOVEFAIL", pRel, the result
end Batch.MoveDone

on Batch.Log pWhat, pRel, pNote
   put the long system date && the long time & tab & pWhat & tab & pRel & tab & pNote & cr after URL ("file:" & sPaths["log"])
end Batch.Log

-- every folder of a path, from /home down (the //wsl$/Ubuntu part already exists)
on Batch.MakeFolders pPath
   local tSoFar, tPart, n
   set the itemDel to "/"
   put 0 into n
   repeat for each item tPart in pPath
      add 1 to n
      put tPart after tSoFar
      if n > 4 and tPart is not empty and there is not a folder tSoFar then create folder tSoFar
      put "/" after tSoFar
   end repeat
end Batch.MakeFolders

function Batch.FreeName pPath
   local n, tTry
   repeat with n = 2 to 99
      put Batch.NoExt(pPath) & "_" & n & "." & Batch.Ext(pPath) into tTry
      if there is not a file tTry then return tTry
   end repeat
   return pPath & "_" & the seconds
end Batch.FreeName

function Batch.Ext pPath
   set the itemDel to "."
   return item -1 of pPath
end Batch.Ext

-- the crashed ones again, with their custom data sampled (what usually hangs the harvester)
on Batch.RetryCrashed pOnlyNew
   local tRel
   if sRunning then exit Batch.RetryCrashed
   Batch.Scan
   repeat for each line tRel in sList
      if sState[tRel] is "CRASHED" and not (pOnlyNew is true and sRetried[tRel] is true) then
         put "waiting" into sState[tRel]
         put true into sForceSample[tRel]
         Batch.Log "RETRY", tRel, "custom data sampled"
      end if
   end repeat
   Batch.ShowList
   put empty into sTried
   put false into sStop
   put true into sRunning
   put 0 into sDone
   put 0 into sFailed
   put the seconds into sStarted
   send "Batch.Next" to me in 100 milliseconds
end Batch.RetryCrashed

-- crashed stacks never retried before (the automatic retry at the end of a run)
function Batch.AutoRetryCount
   local tRel, n
   put 0 into n
   repeat for each line tRel in sList
      if sState[tRel] is "CRASHED" and sRetried[tRel] is not true then add 1 to n
   end repeat
   return n
end Batch.AutoRetryCount

function Batch.NoExt pRel
   local tName
   set the itemDel to "/"
   put item -1 of pRel into tName
   set the itemDel to "."
   if the number of items of tName > 1 then delete item -1 of tName
   set the itemDel to "/"
   put tName into item -1 of pRel
   return pRel
end Batch.NoExt

-- a short text report: counts, and every failure
function Batch.Report
   local tOut, tRel
   put (the number of lines of sList) && "stacks;" && Batch.Count("moved") && "harvested and moved this run," && \
         Batch.Count("waiting") && "waiting," && Batch.Count("FAIL") && "failed," && Batch.Count("CRASHED") && "crashed" & cr into tOut
   repeat for each line tRel in sList
      if sState[tRel] is among the items of "FAIL,CRASHED" then put sState[tRel] & tab & tRel & cr after tOut
   end repeat
   if sRunning then put "running..." & cr after tOut
   return tOut
end Batch.Report

-- for debugging the batch from a script: what it believes right now
function Batch.Debug
   local tOut, tKey
   put "running=" & sRunning & " list=" & the number of lines of sList & " tried=" & the number of lines of the keys of sTried & cr into tOut
   repeat for each key tKey in sState
      put sState[tKey] & tab & tKey & cr after tOut
   end repeat
   return tOut
end Batch.Debug
