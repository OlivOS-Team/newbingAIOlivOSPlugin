import OlivOS

import urllib
import traceback
import time
import hashlib
import os
import codecs
import asyncio
import json
import sys

from newbingAIOlivOSPlugin.EdgeGPT import Chatbot, ConversationStyle

global_Proc = None

configDir = 'plugin/data/newbingAIOlivOSPlugin/'
configPath = 'plugin/data/newbingAIOlivOSPlugin/config.json'
runDir = sys.argv[0]

def logProc(Proc, level, message, segment):
    Proc.log(
        log_level = level,
        log_message = message,
        log_segment = segment
    )

def globalLog(level, message):
    global global_Proc
    if global_Proc != None:
        logProc(global_Proc, level, message, [('newbingAIOlivOSPlugin', 'default')])

class Event:
    def init(plugin_event, Proc):
        global global_Proc
        global_Proc = Proc

    def private_message(plugin_event, Proc):
        if replyCONTEXT_regGet(
            plugin_event=plugin_event,
            tmp_reast_str=plugin_event.data.message
        ):
            pass
        else:
            unity_message(plugin_event, Proc)

    def group_message(plugin_event, Proc):
        if replyCONTEXT_regGet(
            plugin_event=plugin_event,
            tmp_reast_str=plugin_event.data.message
        ):
            pass
        else:
            unity_message(plugin_event, Proc)

    def menu(plugin_event, Proc):
        openConfig()

def unity_message(plugin_event:OlivOS.API.Event, Proc:OlivOS.pluginAPI.shallow):
    messageObj = OlivOS.messageAPI.Message_templet(
        'olivos_string',
        plugin_event.data.message
    )
    message = ''
    for messageObj_this in messageObj.data:
        if type(messageObj_this) is OlivOS.messageAPI.PARA.text:
            message += messageObj_this.OP()
    if message.lower().startswith('.nbg') \
    or message.lower().startswith('。nbg') \
    or message.lower().startswith('/nbg') \
    or message.lower().startswith('.nb') \
    or message.lower().startswith('。nb') \
    or message.lower().startswith('/nb'):
        flagGroupChat = False
        if message.lower().startswith('.nbg'):
            message = message.lstrip('.nbg')
            flagGroupChat = True
        elif message.lower().startswith('。nbg'):
            message = message.lstrip('。nbg')
            flagGroupChat = True
        elif message.lower().startswith('/nbg'):
            message = message.lstrip('/nbg')
            flagGroupChat = True
        elif message.lower().startswith('.nb'):
            message = message.lstrip('.nb')
        elif message.lower().startswith('。nb'):
            message = message.lstrip('。nb')
        elif message.lower().startswith('/nb'):
            message = message.lstrip('/nb')
        message = message.lstrip(' ')
        ask = message
        ask_id = None
        if 'qq' == plugin_event.platform['platform']:
            try:
                ask_id = plugin_event.data.message_id
            except:
                pass
        if len(ask) == 0:
            ask = '你好'
        if len(ask) > 0:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            bot = startAI()
            group_id = None
            try:
                group_id = plugin_event.data.group_id
            except:
                group_id = None
            hash_list = [group_id, plugin_event.data.user_id]
            if flagGroupChat and group_id is not None:
                hash_list = [group_id, None]
                eventReply(plugin_event, 'New Bing 现在将会开始回答大家的问题，正在连接', ask_id)
            else:
                eventReply(plugin_event, 'New Bing 现在将会开始回答您的问题，正在连接', ask_id)
            while True:
                #ask_id = None
                if ask == None:
                    globalLog(2, '等待用户回复：%s' % str(hash_list))
                    ask_obj = replyCONTEXT_regWait(
                        plugin_event=plugin_event,
                        flagBlock='allowCommand',
                        hash=contextRegHash(hash_list)
                    )
                    if ask_obj != None:
                        ask = ask_obj['res']
                        ask_id = ask_obj['msgid']
                resAn = None
                if ask != None:
                    globalLog(2, '等待AI回复：%s ：%s' % (str(hash_list), ask))
                    try:
                        res = loop.run_until_complete(getAI(bot, ask))
                    except Exception as e:
                        resAn = '连接中断了！别担心，New Bing 稍后会回答您的问题'
                        eventReply(plugin_event, resAn, ask_id)
                        break
                    if res != None:
                        try:
                            for it_this in res['item']['messages']:
                                if type(it_this) is dict \
                                and 'author' in it_this \
                                and 'bot' == it_this['author']:
                                    resAn = it_this['text']
                        except Exception as e:
                            traceback.print_exc()
                            resAn = None
                            resAn = '连接出错了！别担心，New Bing 稍后会回答您的问题'
                            eventReply(plugin_event, resAn, ask_id)
                            break
                if resAn == None:
                    resAn = '对话已结束！New Bing 期待与您的再次相遇'
                    eventReply(plugin_event, resAn, ask_id)
                    break
                else:
                    eventReply(plugin_event, resAn, ask_id)
                ask = None
            loop.run_until_complete(endAI(bot))
            loop.close()

def startAI():
    proxy = None
    proxy_data = urllib.request.getproxies()
    cookies = {}
    if 'http' in proxy_data:
        proxy = proxy_data['http']
    try:
        cookies = readConfig()
    except:
        releaseConfig()
    bot = Chatbot(
        cookies = cookies,
        proxy = proxy
    )
    return bot

async def endAI(bot:Chatbot):
    await bot.close()

async def getAI(bot,ask:str):
    res = await bot.ask(
        prompt = ask,
        conversation_style = ConversationStyle.creative,
        wss_link = "wss://sydney.bing.com/sydney/ChatHub"
    )
    return res

def get_system_proxy():
    res = urllib.request.getproxies()
    for res_this in res:
        res[res_this] = res[res_this].lstrip('%s://' % res_this)
    return res

contextWaitTime = 60 * 2
contextFeq = 0.1
dictReplyContextReg = {}

def replyCONTEXT_regGet(plugin_event:OlivOS.API.Event, tmp_reast_str:str):
    tmp_hagID = None
    try:
        tmp_hagID = plugin_event.data.group_id
    except:
        pass
    tmp_bothash = plugin_event.bot_info.hash
    tmp_userID = plugin_event.data.user_id
    tmp_msgid = None
    if 'qq' == plugin_event.platform['platform']:
        try:
            tmp_msgid = plugin_event.data.message_id
        except:
            pass
    tmp_hash_list = []
    tmp_hash_list.append(contextRegHash([tmp_hagID, tmp_userID]))
    if tmp_hagID is not None:
        tmp_hash_list.append(contextRegHash([tmp_hagID, None]))
    res_list = []
    for tmp_hash in tmp_hash_list:
        res = False
        flagResult = False
        if (
            tmp_bothash in dictReplyContextReg
        ) and (
            tmp_hash in dictReplyContextReg[tmp_bothash]
        ) and (
            'block' in dictReplyContextReg[tmp_bothash][tmp_hash]
        ):
            if (
                'res' in dictReplyContextReg[tmp_bothash][tmp_hash]
            ) and (
                dictReplyContextReg[tmp_bothash][tmp_hash]['res'] == None
            ):
                tmp_data_block = dictReplyContextReg[tmp_bothash][tmp_hash]['block']
                if type(tmp_data_block) == bool:
                    res = dictReplyContextReg[tmp_bothash][tmp_hash]['block']
                    flagResult = True
                elif type(tmp_data_block) == str:
                    if tmp_data_block == 'allowCommand':
                        flag_is_command = False
                        if tmp_reast_str.startswith('.nbg') \
                        or tmp_reast_str.startswith('。nbg') \
                        or tmp_reast_str.startswith('/nbg') \
                        or tmp_reast_str.startswith('.nb') \
                        or tmp_reast_str.startswith('。nb') \
                        or tmp_reast_str.startswith('/nb') \
                        or tmp_reast_str.startswith('.bye') \
                        or tmp_reast_str.startswith('。bye') \
                        or tmp_reast_str.startswith('/bye'):
                            flag_is_command = True
                        if flag_is_command:
                            res = False
                            dictReplyContextReg[tmp_bothash].pop(tmp_hash)
                        else:
                            res = True
                            flagResult = True
                        time.sleep(contextFeq * 2)
                    else:
                        res = True
                if flagResult:
                    dictReplyContextReg[tmp_bothash][tmp_hash]['res'] = tmp_reast_str
                    dictReplyContextReg[tmp_bothash][tmp_hash]['msgid'] = tmp_msgid
            else:
                res = False
        res_list = []
    if True in res_list:
        res = True
    return res

def contextRegHash(data:list):
    res = None
    hash_tmp = hashlib.new('md5')
    for data_this in data:
        if type(data_this) == str:
            hash_tmp.update(str(data_this).encode(encoding='UTF-8'))
    res = hash_tmp.hexdigest()
    return res

def replyCONTEXT_regWait(plugin_event:OlivOS.API.Event, flagBlock = True, hash:'str|None' = None):
    res = None
    tmp_hash = None
    tmp_bothash = plugin_event.bot_info.hash
    tmp_block = flagBlock
    if hash != None:
        tmp_hash = hash
    if tmp_bothash not in dictReplyContextReg:
        dictReplyContextReg[tmp_bothash] = {}
    dictReplyContextReg[tmp_bothash][tmp_hash] = {
        'hash': tmp_hash,
        'block': tmp_block,
        'msgid': None,
        'res': None
    }
    feq = contextFeq
    count = contextWaitTime * int(1 / feq)
    while count > 0:
        count -= 1
        time.sleep(feq)
        if tmp_bothash in dictReplyContextReg \
        and tmp_hash in dictReplyContextReg[tmp_bothash]:
            if 'res' in dictReplyContextReg[tmp_bothash][tmp_hash] \
            and dictReplyContextReg[tmp_bothash][tmp_hash]['res'] != None:
                res = dictReplyContextReg[tmp_bothash][tmp_hash]
                break
        else:
            break
    return res


def eventReply(plugin_event:OlivOS.API.Event, message:str, msgid:'str|None' = None):
    res = message
    if msgid != None:
        res = '[OP:reply,id=%s]%s' % (str(msgid), message)
    plugin_event.reply(res)

def releaseConfig():
    try:
        os.makedirs(configDir)
    except:
        pass
    with open(configPath, 'w', encoding='utf-8') as f:
        f.write('{}')

def readConfig():
    res = {}
    with open(configPath, 'rb') as f:
        res = json.loads(formatUTF8WithBOM(f.read()).decode('utf-8'))
    return res

def openConfig():
    if not os.path.exists(configPath):
        releaseConfig()
    os.popen('notepad.exe %s' % configPath)

def formatUTF8WithBOM(data:bytes):
    res = data
    if res[:3] == codecs.BOM_UTF8:
        res = res[3:]
    return res
