# -*- coding: utf-8 -*-
import scrapy
import re
import json
from youtube_dl_scrapy.items import *
from youtube_dl_scrapy.youtube_dl.YoutubeDL import my_definited_urls
from youtube_dl_scrapy.youtube_dl import main
import hashlib
class YoutubeDlSpider(scrapy.Spider):
    name = 'youtube_dl'
    start_urls = ['https://www.bilibili.com/bangumi/play/ep232125']
    def start_requests(self):
        parameter=['-g',"--rm-cache-dir"]
        for i in self.start_urls:
            if "bilibili" in i:
                yield scrapy.Request(url=i,callback=self.bili_parse)
            else:
                parameter.append(i)
        if len(parameter)==2:
            pass
        else:
            print("waiting for youtube_dl get urls")
            main(parameter)
            print("get youtube_dl urls")
            for i in my_definited_urls:
                my_url_dict=my_definited_urls[i]
                for j in my_url_dict:
                    name=str(j).rsplit(".",1)[0]
                    filetype=str(j).rsplit(".",1)[-1]
                    yield scrapy.Request(url=my_url_dict[j],callback=self.savefile,meta={"name":name,"filetype":filetype,"fileid":None,"id":None,"end":None})

    def parse(self, response):
        pass
    def bili_parse(self,response):
        if isinstance(response.body,bytes):
            file=str(response.body.decode("utf8"))
        else:
            file=str(response.body)
        temp=re.search(r"__INITIAL_STATE__=(\{.*\});\(fun",file,re.S)
        temp=str(temp.group(1))
        temp=json.loads(temp)
        url="https://www.kanbilibili.com/api/video/%d/download?cid=%d&quality=64&page=%d"
        if "videoData" in temp:
            videodata=temp['videoData']
            pagelist=videodata['pages']
            aid=videodata["aid"]
            for item in pagelist:
                page=item['page']
                cid=item['cid']
                name=item['part']
                new_url=url%(int(aid),int(cid),int(page))
                yield scrapy.Request(url=new_url,callback=self.bili_get_json,meta={"name":name,"id":page,"Referer":response.url})
        else:
            title=temp["mediaInfo"]["title"]
            pagelist=temp["epList"]
            name=str(title)+"%03d"
            for item in pagelist:
                aid=item["aid"]
                cid=str(item["cid"])
                page=item["index"]
                access_id=int(item["episode_status"])
                if access_id==2:
                    if len(item["index_title"])==0:
                        new_name=name%(int(page))
                    else:
                        new_name=title+"_"+item["index_title"]
                    if "bangumi" in response.url:
                        secretkey="9b288147e5474dd2aa67085f716c560d"
                        temp="cid=%s&module=bangumi&otype=json&player=1&qn=112&quality=4"%(str(cid))
                        sign_this = hashlib.md5(bytes(temp+secretkey, 'utf-8')).hexdigest()
                        new_url  =  "https://bangumi.bilibili.com/player/web_api/playurl?"+temp+'&sign=' + sign_this
                    else:
                        new_url=url%(int(aid),int(cid),int(page))
                    yield scrapy.Request(url=new_url,callback=self.bili_get_json,meta={"name":new_name,"id":page,"Referer":response.url})
                else:
                    pass

    def bili_get_json(self,response):
        if isinstance(response.body,bytes):
            temp_dict=json.loads(response.body.decode("utf8"))
        else:
            temp_dict = json.loads(str(response.body))
        if "err" in temp_dict:
            if temp_dict['err'] is None:
                my_url_list=temp_dict["data"]["durl"]
                filetype=temp_dict["data"]["format"][0:3]
                end_id=len(my_url_list)
                for i in my_url_list:
                    fileid=i["order"]
                    link_url=i["url"]
                    if int(fileid)==int(end_id):
                        end=True
                    else:
                        end=False
                    yield scrapy.Request(url=link_url,callback=self.savefile,headers={"Origin":"https://www.bilibili.com","Referer":response.meta["Referer"]},
                                         meta={"name":response.meta["name"],"id":response.meta["id"],"filetype":filetype,"fileid":fileid,"end":end})
        else:
            my_url_list=temp_dict["durl"]
            filetype=temp_dict["format"][0:3]
            end_id=len(my_url_list)
            for i in my_url_list:
                fileid=i["order"]
                link_url=i["url"]
                if int(fileid)==int(end_id):
                    end=True
                else:
                    end=False
                yield scrapy.Request(url=link_url,callback=self.savefile,headers={"Origin":"https://www.bilibili.com","Referer":response.meta["Referer"]},
                                     meta={"name":response.meta["name"],"id":response.meta["id"],"filetype":filetype,"fileid":fileid,"end":end})
    def savefile(self,response):
        item=FileItem()
        if response.meta['fileid'] is None and response.meta['end'] is None and response.meta['id'] is None:
            print("get %s"%(response.meta['name']))
            item['fileid']=None
            item['end']=None
            item['id']=None
        else:
            print("get %s__%d"%(response.meta['name'],int(response.meta['fileid'])))
            item['fileid']=int(response.meta['fileid'])
            item['end']=response.meta['end']
            item['id']=int(response.meta['id'])
        item['name']=response.meta['name']
        item['filetype']=response.meta['filetype']
        item['content']=response.body
        yield item
