                                         --适老化智慧家居控制系统
function mode1()
    --卫生间
    Add_DataPoint("led1", 1001, "int");  --照明灯DO0
    Add_DataPoint("fan1", 1002, "int");  --风扇DO1
    Add_DataPoint("fuled1", 1003, "int");  --辅灯DO2
    Add_DataPoint("wendu", 1004, "int");  --温度
    Add_DataPoint("shidu", 1005, "int"); --湿度
	
    --客厅
    Add_DataPoint("zhuled2", 1006, "int");  --主灯DO3
    Add_DataPoint("fuled2", 1007, "int");  --辅灯D04
	Add_DataPoint("curtain2", 1008, "int");  --客厅窗帘1
	Add_DataPoint("door", 1009, "int");  --门磁
	Add_DataPoint("duishe", 1010, "int");  --红外对射
	Add_DataPoint("huoyan", 1011, "int");  --火焰

	--厨房
	Add_DataPoint("fan3", 1013, "int");  --风扇DO5
	Add_DataPoint("fuled3", 1014, "int");  --辅灯DO6
	Add_DataPoint("led3", 1015, "int");  --照明灯DO7
	Add_DataPoint("smog", 1016, "int");  --烟雾
	
	--卧室
	Add_DataPoint("yeled4", 1018, "int");  --夜灯DO8
	Add_DataPoint("zhuled4", 1019, "int");  --主灯DO9
	Add_DataPoint("fuled4", 1020, "int");  --辅灯DO10
	Add_DataPoint("guangzhao", 1021, "int"); --光照度
	Add_DataPoint("curtain4", 1022, "int");  --卧室窗帘2
	Add_DataPoint("renti", 1023, "int");  --人体
	
	--添加另外需求
	Add_DataPoint("th", 1030, "int");  --天黑小夜灯
	Add_DataPoint("diedao", 1024, "int");--跌倒传感器
	Add_DataPoint("xcgl", 1100, "int");  --小车过来
	Add_DataPoint("xchq", 1101, "int");  --小车回去
	Add_DataPoint("wavpaly", 1125, "str");--背景音乐
	Add_DataPoint("zzd", 1111, "int");--脑电波
	Add_DataPoint("mxd", 1111, "int");--脑电波

	Write_DataPoint("xchq", 1);--初始化小车状态为小车过来
	door_state=1--初始化客厅门为打开
	count=0--初始化计时门打开变量
	while 1 do
	delay(100)
	curtain2, ret = Read_sys_register(1008, "int");--客厅窗帘控制判断
	if ret==1 then
		if curtain2==0 then--关闭窗帘
		curtain_485_control(1, 0xfdfe, 0x02)
		end
		if curtain2==100 then--打开窗帘
		curtain_485_control(1, 0xfdfe, 0x01)
		end
	end
	delay(100)
	wd,sd,ret=ModbusRTU_read_input_register(1,15,0x012b,2,"int")--读取温湿度传感器
	if ret==1 then
		Write_DataPoint("wendu",wd);
		Write_DataPoint("shidu",sd);
	    delay(100);
	    if sd>=8000 then
	    	Write_DataPoint("fan1",1);
	    	Write_sys_register (1002,1,"int");--打开卫生间风扇
		else
	    	Write_DataPoint("fan1",0);
	    	Write_sys_register (1002,0,"int");--关闭卫生间风扇
		end
	end
		delay(100)
	curtain4, ret = Read_sys_register(1022, "int");--卧室窗帘控制判断
	if ret==1 then
		if curtain4==0 then--关闭窗帘
			curtain_485_control(1, 0xfefe, 0x01)
		end
		if curtain4==100 then--打开窗帘
			curtain_485_control(1, 0xfefe, 0x02)
		end
	end
		delay(100)
--网关通过串口1获取光照度值
	gz, ret=ModbusRTU_read_input_register(1,12,0x012b,1,"int")--读取光照度传感器
	if ret==1 then
		Write_DataPoint("guangzhao",gz);
	    delay(100);
	    if gz<=40 then--光照度小于40执行
			Write_DataPoint("curtain2",0);--关闭客厅窗帘
			Write_DataPoint("curtain4",0);--关闭卧室窗帘
			Write_DataPoint("th",1);--打开人体小夜灯标识
			Write_sys_register (1008,0,"int");--关闭客厅窗帘
			Write_sys_register (1022,0,"int");--关闭卧室窗帘
			Write_sys_register (1030,1,"int");--打开人体小夜灯标识
	    else
			Write_DataPoint("curtain2",100);--打开客厅窗帘
			Write_DataPoint("curtain4",100);--打开卧室窗帘
			Write_DataPoint("th",0);--打开人体小夜灯标识
			Write_DataPoint("yeled4",0);	--关闭小夜灯
		    Write_sys_register (1008,100,"int");--打开客厅窗帘
			Write_sys_register (1022,100,"int");--打开卧室窗帘
			Write_sys_register (1030,0,"int");--关闭人体小夜灯标识
			Write_sys_register (1018,0,"int");	--关闭小夜灯
		end
	end
	delay(100);
	hy,ds,dr,sg,rt,ret = ModbusRTU_read_input_status(1, 1, 0, 5);	 --读取开关量设备的寄存器的数据写到网关变量
	if ret==1 then
	    Write_DataPoint("huoyan",hy );
        Write_DataPoint("duishe", ds);
        Write_DataPoint("door", dr);
        Write_DataPoint("smog", sg);
        Write_DataPoint("renti", rt);
	    delay(100);
	    th= Read_sys_register(1030, "int")--读取人体小夜灯
	    if th==1 then--光照度小于等于40
			if rt==0 then--人体感应到没人
				Write_DataPoint("yeled4",0);	--关闭小夜灯
				Write_sys_register (1018,0,"int");--关闭小夜灯
			else
				Write_DataPoint("yeled4",1);	--打开小夜灯
				Write_sys_register (1018,1,"int");--打开小夜灯
			end
		end
		if dr==0 then  --0关 1开
			door_state=0
			count=0
		elseif door_state==0 then --开门触发
			door_state=1
			if ds==0  then --进门触发
			    playwav("/wav/dooropen.wav", 1) --欢迎爷爷回家
			     Write_DataPoint("fuled2",1);--打开客厅辅灯
			     Write_sys_register (1007,1,"int");--打开客厅辅灯
			     end
			if dr==1 and ds==1 then --关门触发
			    playwav("/wav/doorclose.wav", 1) --爷爷记得带药
			    Write_DataPoint("fuled2",0);--关闭客厅辅灯
			    Write_sys_register (1007,0,"int");--关闭客厅辅灯
			end
			end
		if dr==1 then--门打开后计时
		    count=count+1
			if count>1 then
			    count=0
				playwav("/wav/door.wav", 1)
			end
		end
	    if sg==1 then--感应到烟雾
	    	Write_DataPoint ("fan3",1);--开启厨房风扇
	    	Write_sys_register (1013,1,"int");--开启厨房风扇
			playwav("/wav/yanwu.wav", 1)
	    else
	    	Write_DataPoint ("fan3",0);--关闭厨房风扇
	    	Write_sys_register (1013,0,"int");--关闭厨房风扇
	    end
	    	delay(100)
	    if hy==1 then--感应到火焰
	    	playwav("/wav/huoyan.wav", 1)
	    end
	end
	delay(100);
	--厨房控制
    led1, ret= Read_sys_register(1001, "int");--厨房照明灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 0, led1)
	end
	delay(100)
	fan1, ret = Read_sys_register(1002, "int");--厕所风扇控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 1, fan1)
	end
	delay(100)
	fuled1, ret = Read_sys_register(1003, "int");--厨房辅灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 2, fuled1)
	end
	delay(100)

	--客厅控制
	zhuled2, ret = Read_sys_register(1006, "int");--客厅主灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 3, zhuled2)
	end
	delay(100)
	fuled2, ret = Read_sys_register(1007, "int");--客厅辅灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 4, fuled2)
	end
	delay(100)


	--厨房
	fan3, ret= Read_sys_register(1013, "int");--厨房风扇控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 5, fan3)
	end
	delay(100)
	fuled3, ret = Read_sys_register(1014, "int");--厨房辅灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 6, fuled3)
	ModbusRTU_force_single_coil(1, 1, 5, fan3)
	end
	delay(100)
	led3, ret = Read_sys_register(1015, "int");--厨房照明灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 7, led3)
	end
	delay(100)

	--卧室
	yeled4,ret = Read_sys_register(1018, "int");--卧室夜灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 8, yeled4)
	end
	delay(100)
	zhuled4, ret = Read_sys_register(1019, "int");--卧室主灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 9, zhuled4)
	end
	delay(100)
	fuled4, ret = Read_sys_register(1020, "int");--卧室辅灯控制判断
	if ret==1 then
	ModbusRTU_force_single_coil(1, 1, 10,fuled4)
	end

	flag, ret= Read_DataPoint("xcgl");--查看下小车过来的状态值是否改变，如果改变就写入云变量。并且与小车回去互斥
	if ret==2 then
		if flag==1 then
			Write_DataPoint("xcgl",1);
			Write_DataPoint("xchq",0);
		end
		if flag==0 then
			Write_DataPoint("xcgl",0);
			Write_DataPoint("xchq",1);
		end
	end
	delay(100)
	flag, ret= Read_DataPoint("xchq");--查看下小车回去的状态值是否改变，如果改变就写入云变量。并且与小车过来互斥
	if ret==2 then
		if flag==1 then
			Write_DataPoint("xcgl",0);
			Write_DataPoint("xchq",1);
		end
		if flag==0 then
			Write_DataPoint("xcgl",1);
			Write_DataPoint("xchq",0);
		end
	end
	
	delay(100)
	cmd, ret= Read_DataPoint("wavpaly");--查看下背景音乐播放的状态值是否改变，如果改变就播放背景音乐
	if ret==2 then
		if cmd=="stop" then
			stopwav();
		else
			 playwav("/wav/relax.wav", 1)
		    playwav("/wav/"..cmd, 0)
		end
	end
	s, ret= Read_DataPoint("diedao");--查看跌倒传感器的
	if ret==2 then
		if s==1 then
			playwav("/wav/down.Wav", 1)
			Write_DataPoint("Xcgl",1);--小车过来开启
		    Write_DataPoint("Xchq",0);--小车回去关闭
		else
		    Write_DataPoint("Xcgl",0);--小车过来关闭
		    Write_DataPoint("Xchq",1);--小车回去开启
		end
	end
	--网关IP, Modbus端口, 设备地址，从10开始一共1个寄存器
	ret,mode = ModbusTCP_read_hold_register(ip,5002,1,10,1, "int")
	if ret==1 then
		
		if mode ==4 then --跌倒
		--网关IP, Modbus端口, 设备地址，从1000开始一共2个寄存器
		   ret,num,s = ModbusTCP_read_hold_register(ip,5002,1,1000,2, "int")
			   if num>0 and s==0 then
				 playwav("/wav/down.Wav", 1)
				 Write_DataPoint("Xcgl",1);--小车过来开启
				 Write_DataPoint("Xchq",0);--小车过来关闭
			   end
		elseif mode ==6 then --明火
		   ret,fire = ModbusTCP_read_hold_register(ip,5002,1,1000,1, "int")
		   if fire~=0 then
			 playwav("/wav/fire.wav", 1)
		   end
		end
	end
	end
end
release(); --配置为发布版本123
--设置网口信息
ip = "192.168.1.227"
--在该处设置网络参数ip、掩码、网关
sys_set_com(1, 9600, "none", 8, 1);
sys_set_eth0(ip, "255.255.255.0", "192.168.1.1")
sys_set_eth0_dns("114.114.114.114")
HTTP_service(8000, 4);--设置上传数据格式
ModbusTCP_service(502,1)
--配置变量名对应中文名称
local config = {
  ["卫生间照明灯"] = "led1",
  ["卫生间风扇"] = "fan1",
  ["卫生间辅灯"] = "fuled1",
  ["卫生间温度"] = "wendu",
  ["卫生间湿度"] = "shidu",

  ["客厅窗帘"]="curtain2",
  ["客厅主灯"]="zhuled2",
  ["客厅辅灯"] = "fuled2",
  ["客厅门磁"] = "door",
  ["客厅红外对射"] = "duishe",
  ["客厅火焰"]="huoyan",

  ["厨房风扇"]="fan3",
  ["厨房辅灯"]="fuled3",
  ["厨房照明灯"]="led3",
  ["厨房烟雾"]="smog",

  ["卧室夜灯"]="yeled4",
  ["卧室主灯"]="zhuled4",
  ["卧室辅灯"]="fuled4",
  ["卧室光照度"]="guangzhao",
  ["卧室窗帘"]="curtain4",
  ["卧室人体"]="renti",

  ["小车过来模式"]="xcgl",
  ["小车回去模式"]="xchq",
  ["背景音乐"]="wavpaly",
  ["跌倒传感器"]="diedao",
  ["192.168.1.227:8000"] = "HTTP_service_URL"
}
--小智的MCP接入点
MCP_service("wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQwMTEyMywiYWdlbnRJZCI6NDgwMzE0LCJlbmRwb2ludElkIjoiYWdlbnRfNDgwMzE0IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc1MjU2MzYzOH0.EdtY9msrrFCRAKGMfnvBTZQRrcuRdX2Lg8dw8VTu762GmMqcxBlY6fUCRd6SaxOEtN-wb3Ae1PjS7W5XqZTVxA",config)
--播报欢迎使用适老化系统
playwav("/wav/welcome.wav", 1)
mode1();


