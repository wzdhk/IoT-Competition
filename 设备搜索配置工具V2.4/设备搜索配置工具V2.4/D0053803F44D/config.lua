function mode1()  
	HA_Add_DataPoint("sos", "报警灯", "switch")
	HA_Add_DataPoint("fan", "风扇", "switch")
	HA_Add_DataPoint("light", "灯泡", "switch")
	HA_Add_DataPoint("kongtiao", "空调", "switch")
	HA_Add_DataPoint("curtain_val", "窗帘", "cover")
	
	HA_Add_DataPoint("door", "门磁", "binary_sensor")
	HA_Add_DataPoint("renti", "人体", "binary_sensor")
	HA_Add_DataPoint("smog", "烟雾", "binary_sensor")
	HA_Add_DataPoint("hongwai", "红外对射", "binary_sensor")
	
	HA_Add_DataPoint("wendu", "温度", "sensor", "°C")
	HA_Add_DataPoint("shidu", "湿度", "sensor", "%RH")
	HA_Add_DataPoint("Illuminance", "光照度", "sensor", "Lx")
	HA_Add_DataPoint("PM25", "PM2.5", "sensor", "μg/m3")
	HA_Add_DataPoint("PM10", "PM10", "sensor", "μg/m3")
	

    --1-8为4路io控制器485 地址为4
	Add_DataPoint("sos", 1001, "int");  --报警模块（读写）
    Add_DataPoint("fan", 1002, "int");  --风扇
    Add_DataPoint("light", 1003, "int");  --灯泡
    	
	Add_DataPoint("kongtiao", 1030, "int");	--空调
	Add_DataPoint("curtain", 1031, "int");	--窗帘0停止，1全关，2全开
	Add_DataPoint("curtain_val", 1032, "int");	--窗帘位置
	
	Add_DataPoint("hongwai",1005,"int");	--红外对射（只读）
	Add_DataPoint("door",1006,"int");	--门磁（只读）
	Add_DataPoint("renti",1007,"int");	--识别人（只读）
	Add_DataPoint("smog",1008,"int");	--烟雾（只读）
	
	--温湿度地址为1 光照为2 空气质量为3
	Add_DataPoint("wendu",1011,"int");	--温度（只读）	
	Add_DataPoint("shidu",1012,"int");	--湿度（只读）
	Add_DataPoint("Illuminance",1013,"int");	--光照（只读）
	Add_DataPoint("PM25",1014,"int");		--空气质量2.5（只读）
	Add_DataPoint("PM10", 1015, "int");	--空气质量10
	Add_DataPoint("tem", 1016, "int");	--温度AI
	
	Add_DataPoint("sos_light", 1002, "int");  --应急指示灯
    Add_DataPoint("switch", 1004, "int");  --智能断路器
	Add_DataPoint("school_mode",1015,"int");	--上课模式/0放学，1上学
	
	Add_DataPoint("energy_consumption",1020,"int");	--能耗
	Add_DataPoint("currents",1022,"int");	--电流
	Add_DataPoint("voltage",1023,"int");	--电流
	
	Add_DataPoint("electric_quantity",1024,"int");	--用电量
	
	
	
	Write_DataPoint("curtain_val",100);
    count=10
while 1 do
	delay(100);
		--
	--hw,dr,rt,sg,ret = ModbusRTU_read_input_status(2, 2, 0, 4);	 --读取开关量设备的寄存器的数据写到网关变量
	--if ret==1 then
	--	if hw == 0 then
	--	Write_DataPoint("hongwai",1 );
	--	elseif hw==1 then
	--	Write_DataPoint("hongwai",0 );
	--	end
	--	if rt==0 then
	--	Write_DataPoint("renti",1 );
	--	elseif rt==1 then
	--	Write_DataPoint("renti",0 );
	--	end
	--	if sg==0 then
	--	Write_DataPoint("smog",1 );
	--	elseif sg==1 then
	--	Write_DataPoint("smog",0 );
	--	end
	--	Write_DataPoint("door", dr);
	--	delay(50);
	--end
	--val, ret=Read_DataPoint("sos")
	--if ret == 2 then
	--ModbusRTU_force_single_coil(2, 2, 0, val)
	--Write_DataPoint("sos",val);
	--Write_sys_coil(1001,val)
	--delay(50);
	--end
	-- s, ret= Read_sys_coil(1001);--读取报警模块的变量的值写进线圈
	--if ret==1 then --被改变
	--	ModbusRTU_force_single_coil(2, 2, 0, s)
	--	Write_DataPoint("sos",s);
	--	delay(50);
	--end    
	--val, ret=Read_DataPoint("fan")
	--if ret == 2 then
	--ModbusRTU_force_single_coil(2, 2, 1, val)
	--Write_DataPoint("fan",val);
	--Write_sys_coil(1002,val)
	--delay(50);
	--end
	--s, ret= Read_sys_coil(1002);--读取风扇模块的变量的值写进线圈
	--if ret==1 then --被改变
	--  ModbusRTU_force_single_coil(2, 2,1, s)
	--  Write_DataPoint("fan",s);
	--  delay(50);
	--end  
	--val, ret=Read_DataPoint("light")
	--if ret == 2 then
	--ModbusRTU_force_single_coil(2, 2, 2, val)
	--Write_DataPoint("light",val);
	--Write_sys_coil(1003,val)
	--delay(50);
	--end
	--s, ret= Read_sys_coil(1003);--读取灯泡模块的变量的值写进线圈
	--if ret==1 then --被改变
	--  ModbusRTU_force_single_coil(2, 2,2, s)
	--  Write_DataPoint("light",s);
	--  delay(50);
	--end  
	--delay(50);
	--val, ret=Read_DataPoint("kongtiao")
	--if ret == 2 then
	--if val==1 then
	--	ModbusRTU_write_register(2,1,5,0,"int");--在固定寄存器地址5中写入值
	--elseif val==0 then
	--	ModbusRTU_write_register(2,1,5,1,"int");--在固定寄存器地址5中写入值
	--end
	--Write_DataPoint("kongtiao",val);
	--delay(20);
	--Write_sys_coil(1031,val)
	--delay(20);
	--end
	--delay(50);
	--s, ret= Read_sys_coil(1031);--读取空调的变量的值写进线圈
	--if ret==1 then --被改变
	--	if s==1 then
	--		ModbusRTU_write_register(2,1,5,0,"int");--在固定寄存器地址5中写入值
		--	
	--   elseif s==0 then
	--		ModbusRTU_write_register(2,1,5,1,"int");--在固定寄存器地址5中写入值
	--   end
	--   Write_DataPoint("kongtiao",s);
	--  delay(50);
	--end  
	--	val, ret=Read_DataPoint("curtain_val")
	--	if ret == 2 then
	--	curtain_485_control(3, 4, val)
	--	Write_DataPoint("curtain_val",val);
	--	--print(string.format("val:%d, ret:%d", val, ret))
	--	delay(50);
	--	elseif ret ==3 then
	--	curtain_485_control(3, 3)
	--	--print(string.format("val:%d, ret:%d", val, ret))
	--	delay(50);
	--	end
	--	delay(50);
		--	
	--    cl, ret= Read_sys_register(1030, "int");--读取窗帘的变量的值写进线圈
	--	if ret==1 then --被改变
	--		--print(string.format("ret:%d, cl:%d", ret, cl))
	--		if cl==0 then
	--			curtain_485_control(3, 3)--停止
	--			delay(50);
	--		elseif cl==1 then
	--			curtain_485_control(3, 1)--全开100
	--			delay(50);
	--		elseif cl==2 then
	--			curtain_485_control(3, 2)--全关0
	--			delay(50);
	--		end
	--	end 
	--		delay(50);
	--	local position=curtain_485_read_position(3)
	--	Write_DataPoint("curtain_val", position)
	--	--print(string.format("窗帘位置:%d",position))
	--	delay(50);
	--	sd,wd,ret = ModbusRTU_read_hold_register(1, 1, 0, 2, "int");	-- --读取温湿度的寄存器的数据写到网关变量
	--	if ret==1 then
	--		Write_DataPoint("wendu",wd/10);
	--		Write_DataPoint("shidu", sd/10);
	--		delay(50);
	--		--print(string.format("wendu=%d shidu=%d\r\n", wd,sd))
	--	end
		--	
	--	L,ret = ModbusRTU_read_hold_register(1, 11, 6, 1, "int");	 --读光照度的寄存器的数据写到网关变量
	--	if ret==1 then
	--		Write_DataPoint("Illuminance",L);
	--	   delay(50);
	--	end
		--	
	--	pm2,pm10,ret = ModbusRTU_read_hold_register(1, 3, 0, 2, "int");	 --读取空气质量的寄存器的数据写到网关变量
	--	if ret==1 then
	--		Write_DataPoint("PM25",pm2);
	--		Write_DataPoint("PM10",pm10);
	--		 delay(50);
	--	end
		--	
	--	8AI2DI（设备地址为3，功能码04）
	--   awd, ret = ModbusRTU_read_input_register(2, 3, 4006, 1, "int");	--读取土壤温湿度的寄存器的数据写到网关变量
    --   if ret==1 then
    --   	local s=((awd*0.0205-4)*6.25)*10
    --   	if s<0 then
    --   		s=0
    --   	end 
    --   	Write_DataPoint("tem",s);
    --   	--print(string.format("wendu=%.1f\r\n", s/10));
    --   	delay(50);
    --   	end
	--	--以下为LED显示屏翻页功能
	--	count=count+1
	--	if count==11 then	--当计数为11时，显示温湿度
	--		LED_ClearV3(1);
	--		delay(50);
	--		LED_DSV3(1,0,2,12,0,string.format( "     温度:%.1f℃ ",wd/10));
	--		delay(50);
	--		LED_DSV3(1,0,17,12,0,string.format("     湿度:%.1f%%RH ",sd/10));
	--		delay(50);   	
	--	elseif count==21 then --当计数为21时，显示空气质量
	--		LED_ClearV3(1);
	--		delay(50);
	--		LED_DSV3(1,0,2,12,0,string.format( "      PM2.5浓度:%d",pm2));
	--		delay(50);
	--		LED_DSV3(1,0,17,12,0,string.format("      PM10浓度:%d",pm10));
	--		delay(50); 
	--	elseif count==31 then--当计数为31时，显示光照度和门磁状态
	--		LED_ClearV3(1);
	--		delay(50);
	--		LED_DSV3(1,0,2,12,0,string.format("      光照度:%dLux ",L));
	--		delay(50); 
	--		if dr==0 then
	--			LED_DSV3(1,0,17,12,0,"    门磁状态：关闭   ");
	--		else
	--			LED_DSV3(1,0,17,12,0,"    门磁状态：打开   ");
	--		end
	--		delay(50);
	--		count=0	--然后置零，重新显示
	--	end
	--	HA_Update_Data()
end
end
function main()
release(); --配置为发布版本
sys_set_com(1, 9600, "none", 8, 1); --usb串口
sys_set_com(2, 9600, "none", 8, 1); --usb串口
sys_set_com(3, 9600, "none", 8, 1); --usb串口
HA_service("192.168.1.200", 1883, "mqtt123456", "mqtt123456","智能家居控制系统")
HTTP_service(8000, 4);
ModbusTCP_service(502,1)
delay(100)
--LED清屏
LED_ClearV3(1);
curtain_485_control(3, 1)

ModbusRTU_write_register(2,1,5,1,"int");--在固定寄存器地址5中写入值;--初始化空调关
pthread_create("mode1");
 end