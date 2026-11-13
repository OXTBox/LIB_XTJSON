script "XTJSON_Batch"
######################################################################################
## XTJSON BATCH  (13 11 2026)
## One click: every stack waiting in ~/projects/LIB_LLMIN/LIB_XTJSON (any depth) is taken
## apart into XTJSON by LCHarvest2, one after another, and then moved out of the inbox:
##   harvest   -> ~/projects/XTJSON/batch/<same relative path, without extension>/
##   original  -> ~/projects/LIB_LLMOUT/LIB_XTJSON/<same relative path>
## Failures stay in the inbox. Every step is written to XTJSON/batch/_batch_log.tsv
## (START before a stack, OK or FAIL after it). A stack that STARTed and never finished
## crashed the engine: it is marked CRASHED and skipped on the next run, so one bad stack
## can't stop the batch.
## Open this file in LiveCode (IDE or the LIB_MCP standalone): the window builds itself.
##   Run   scan the inbox and harvest everything still waiting (the one click)
##   Scan  just list what is waiting      Stop  finish the current stack, then stop
## From a script:  Batch.Run  /  Batch.Scan  /  Batch.Stop  /  Batch.Report()
## The stacks' own handlers never run (messages are locked while they are loaded).
######################################################################################

constant kHarvestLib = "XT_HarvestLib"
constant kStackExt = "livecode,rev,mc,lc"

local sPaths        -- [projects|inbox|out|done|harvester|log]
local sList         -- the stacks found: relative paths, one per line
local sState        -- [rel] -> waiting / OK / FAIL / CRASHED / moved
local sSize         -- [rel] -> bytes (from the folder listing)
local sStop, sRunning, sIndex, sStarted, sDone, sFailed

-------------------------------------------------------------------- the window

on preOpenStack
   Batch.Paths
   Batch.BuildUI
   Batch.Scan
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
   if there is not a field "Status" then
      reset the templateField
      create field "Status"
      set the rect of field "Status" to 340, 76, 890, 100
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
   put sPaths["projects"] & "/LIB_LLMOUT/LIB_XTJSON" into sPaths["done"]
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
   if sPaths["inbox"] is empty then Batch.Paths
   put empty into sList
   put empty into sSize
   Batch.ScanFolder sPaths["inbox"], empty
   -- what the log says about each stack (the last word wins; START alone = it crashed)
   put empty into sState
   if there is a file sPaths["log"] then put URL ("file:" & sPaths["log"]) into tLog
   set the itemDel to tab
   repeat for each line tLine in tLog
      put item 3 of tLine into tRel
      if tRel is empty then next repeat
      switch item 2 of tLine
         case "START"
            put "CRASHED" into sState[tRel]
            break
         case "OK"
         case "FAIL"
            put item 2 of tLine into sState[tRel]
            break
      end switch
   end repeat
   set the itemDel to comma
   repeat for each line tRel in sList
      if sState[tRel] is empty or sState[tRel] is "OK" then put "waiting" into sState[tRel]
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
   local tRel, tResult
   if sStop then
      put false into sRunning
      Batch.Say "stopped:" && sDone && "harvested," && sFailed && "failed. Run carries on from here."
      exit Batch.Next
   end if
   put empty into tRel
   repeat for each line tRel in sList
      if sState[tRel] is "waiting" then exit repeat
      put empty into tRel
   end repeat
   if tRel is empty then
      put false into sRunning
      Batch.Log "END", empty, sDone && "harvested," && sFailed && "failed in" && (the seconds - sStarted) && "s"
      Batch.Say "finished:" && sDone && "harvested," && sFailed && "failed (" & (the seconds - sStarted) & " s). Log:" && sPaths["log"]
      Batch.ShowList
      exit Batch.Next
   end if
   Batch.Say "harvesting" && tRel && "(" & (sDone + sFailed + 1) & " of" && (sDone + sFailed + Batch.Count("waiting")) & ")..."
   Batch.Log "START", tRel, empty     -- written first: if the engine dies, the next run knows
   put Batch.HarvestOne(tRel) into tResult
   if line 1 of tResult begins with "harvested" then
      Batch.Log "OK", tRel, line 1 of tResult
      Batch.MoveDone tRel
      put "moved" into sState[tRel]
      add 1 to sDone
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
   local tSrc, tOut, tName, tResult, tErr
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
      harvestStack tName, tOut
      put the result into tResult
      lock messages
      if there is a stack tName then delete stack tName
      unlock messages
   catch tErr
      unlock messages
      return "FAIL:" && line 1 of tErr
   end try
   return tResult
end Batch.HarvestOne

-- the original leaves the inbox: LIB_LLMOUT/LIB_XTJSON/<same relative path>
on Batch.MoveDone pRel
   local tTo
   put sPaths["done"] & "/" & pRel into tTo
   set the itemDel to "/"
   Batch.MakeFolders item 1 to -2 of tTo
   set the itemDel to comma
   if there is a file tTo then delete file tTo
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
