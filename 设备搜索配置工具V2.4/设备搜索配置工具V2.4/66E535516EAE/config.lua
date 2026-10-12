function mode1() 
IP="192.168.1.233" -- 网关IP
playwav("/wav/shebei_zijian.wav", 1)
while 1 do
   
	--读取保持寄存器（传感器）
	delay(200);
	L,ret = ModbusRTU_read_hold_register(1, 1, 6, 1, "int");	 --读光照度的寄存器的数据写到网关变量
    if ret==1 then
        Write_DataPoint("Illuminance", L);
        print(string.format("光照度:%dLx\n",L))
	    delay(50);
    end  
    delay(50);
    
    PM2_5, PM10, PM1, ret = ModbusRTU_read_hold_register(1, 2, 0, 3, "int");	--读取空气质量的寄存器的数据写到网关变量
    if ret==1 then
        Write_DataPoint("PM2_5", PM2_5);
        Write_DataPoint("PM10", PM10);
        Write_DataPoint("PM1", PM1);
        print(string.format("PM2_5:%dμg/m?, PM10:%dμg/m?, PM1:%dμg/m?\n",PM2_5, PM10, PM1))
	    delay(50);
    end
    delay(50); 

	flooding,ret = ModbusRTU_read_hold_register(1, 3, 2, 1, "int");	 --读水浸的寄存器的数据写到网关变量
    if ret==1 then
        Write_DataPoint("flooding", flooding);
        print(string.format("水浸:%d\n",flooding))
	    delay(50);
	    -- 如果水浸不为正常
	    if flooding ~= 1 then 
            print("水浸报警！")
            Write_sys_register(1002, 1, "int") -- 启动急停
            SetDO(2, 0)
            delay(50)
            ModbusRTU_write_register(1, 0x33, 1, 255, "int");
            ModbusRTU_write_register(1, 0x33, 2, 0, "int");
            ModbusRTU_write_register(1, 0x33, 3, 0, "int");
            delay(50)
            playwav("/wav/flooding.wav", 1)
	    end
    end  
    delay(50);

	sd,wd,ret = ModbusRTU_read_hold_register(1, 4, 0, 2, "int");	-- --读取温湿度的寄存器的数据写到网关变量
	wd_auto, ret_wd = Read_sys_register(1040, "int"); 
	sd_auto, ret_sd = Read_sys_register(1041, "int"); 
    if ret==1 then
        Write_DataPoint("wendu", wd);
        Write_DataPoint("shidu", sd);
        print(string.format("温度:%.1f℃, 湿度:%.1f%%RH\n", wd/10, sd/10))
        delay(50);
  
        -- 温度自动化
        if wd_auto == 1 then
            if wd/10 > 40 then
                Write_sys_register(1001, 1, "int") -- 启动风扇
                delay(50)
                ModbusRTU_write_register(1, 0x33, 1, 255, "int")
                ModbusRTU_write_register(1, 0x33, 2, 255, "int")
                ModbusRTU_write_register(1, 0x33, 3, 0, "int")
            else
                Write_sys_register(1001, 0, "int") -- 关闭风扇
            end
            delay(50)
        elseif  wd_auto == 0 then --关闭温度自动化开关时
            Write_sys_register(1001, 0, "int") -- 关闭风扇
        end
         
        -- 湿度自动化
        if sd_auto == 1 then
            if sd/10 > 70 then
                Write_sys_register(1002, 0, "int") -- 启动急停
                delay(50)
                Write_sys_register(1001, 1, "int") -- 启动风扇
                delay(50)
                ModbusRTU_write_register(1, 0x33, 1, 0, "int")
                ModbusRTU_write_register(1, 0x33, 2, 255, "int")
                ModbusRTU_write_register(1, 0x33, 3, 255, "int") 
                delay(50)
            else
                Write_sys_register(1002, 1, "int") -- 关闭急停
                delay(50)
                Write_sys_register(1001, 0, "int") -- 关闭风扇
            end
        elseif  sd_auto == 0 then --关闭湿度自动化开关时
            Write_sys_register(1002, 1, "int") -- 关闭急停
            delay(50)
            Write_sys_register(1001, 0, "int") -- 关闭风扇
        end
    end
    delay(50);
    
    fan,ret= Read_sys_register(1001, "int"); -- 风扇
    if ret==1 then
        SetDO(1,fan);
        delay(50);
    end
    delay(50);
    
    E_stop,ret= Read_sys_register(1002, "int"); -- 急停开关
    if ret==1 then
        SetDO(2,E_stop);
        delay(50);
    end    

        -- 读取云变量
        s1,ret1= Read_sys_register(1030, "int"); 
        s2,ret2= Read_sys_register(1031, "int");
        s3,ret3= Read_sys_register(1032, "int");
        s4,ret4= Read_sys_register(1033, "int");
        s5,ret5= Read_sys_register(1034, "int");
        s6,ret6= Read_sys_register(1035, "int");
        s7,ret7= Read_sys_register(1036, "int");
        s8,ret8= Read_sys_register(1037, "int");
        -- 灯光开关
        if ret1 == 1 then
            ModbusRTU_write_register(1, 0x33, 0, s1, "int");
            delay(50);
        end	
        
        -- 开灯
        if s1 == 1 then
            -- 灯光模式
          if ret2 == 1 then
              ModbusRTU_write_register(1, 0x33, 5, s2, "int");
              delay(50);
        end
            
        -- 跑马灯颜色数量
        if ret3 == 1 and s2 == 3 then
            ModbusRTU_write_register(1, 0x33, 12, s3, "int");
            delay(50);
        end
          
        -- 灯带颜色：红绿蓝挡位
          if ret4 == 1 and s2 ~= 3 then
              -- 红色
              if s4 == 1 then
                ModbusRTU_write_register(1, 0x33, 1, 255, "int");
                ModbusRTU_write_register(1, 0x33, 2, 0, "int");
                ModbusRTU_write_register(1, 0x33, 3, 0, "int");
              -- 绿色
              elseif s4 == 2 then
                ModbusRTU_write_register(1, 0x33, 1, 0, "int");
                ModbusRTU_write_register(1, 0x33, 2, 255, "int");
                ModbusRTU_write_register(1, 0x33, 3, 0, "int");
              -- 蓝色
              elseif s4 == 3 then
                ModbusRTU_write_register(1, 0x33, 1, 0, "int");
                ModbusRTU_write_register(1, 0x33, 2, 0, "int");
                ModbusRTU_write_register(1, 0x33, 3, 255, "int");
              end
              delay(50);
            end	
          
            -- 灯光亮度
          if ret5 == 1 then
            ModbusRTU_write_register(1, 0x33, 4, s5, "int");
            delay(50);
          end 

           --灯带颜色 三色值
          if ret6 == 1 then
              ModbusRTU_write_register(1, 0x33, 1, s6, "int");
              delay(50);
          end

          if ret7 == 1 then
              ModbusRTU_write_register(1, 0x33, 1, s7, "int");
              delay(50);
          end
          if ret8 == 1 then
              ModbusRTU_write_register(1, 0x33, 1, s8, "int");
              delay(50);
          end
        end
        
        delay(50);
        
        ret,mode = ModbusTCP_read_hold_register(IP, 5002,1,10,1, "int")
        -- ret1,num1 = ModbusTCP_read_hold_register(IP,5002,1,1000,1, "int")
        ret2, num1, s= ModbusTCP_read_hold_register(IP, 5002, 1, 1000, 2, "int")
        if mode == 5 then -- 反光衣检查
            if num1 > 0 and s == 0 then -- 没穿反光衣大于0 并且 没有检测到反光衣
                print("检查到没穿反光衣！")
                Write_sys_register(1002, 0, "int") -- 启动急停
                SetDO(2, 0)
                delay(50)
                ModbusRTU_write_register(1, 0x33, 5, 2, "int")
                ModbusRTU_write_register(1, 0x33, 1, 255, "int")
                ModbusRTU_write_register(1, 0x33, 2, 0, "int")
                ModbusRTU_write_register(1, 0x33, 3, 0, "int")
                delay(50)
                playwav("/wav/fgy.wav", 1)
            else
                print("检查到有穿反光衣！")
                Write_sys_register(1002, 1, "int") -- 关闭急停
                SetDO(2, 1)
                delay(50)
                ModbusRTU_write_register(1, 0x33, 5, 2, "int")
                ModbusRTU_write_register(1, 0x33, 1, 0, "int")
                ModbusRTU_write_register(1, 0x33, 2, 255, "int")
                ModbusRTU_write_register(1, 0x33, 3, 0, "int")
            end
        elseif mode == 1 then -- 检查画面中是否头盔
            if num1 > 0 and s == 0 then -- 检查画面中是否有头盔，没有头盔就开启急停，否则关闭急停
                print("检查到没戴安全帽！")                
                Write_sys_register(1002, 0, "int") -- 启动急停
                SetDO(2, 0)
                delay(50)
                ModbusRTU_write_register(1, 0x33, 5, 2, "int")
                ModbusRTU_write_register(1, 0x33, 1, 255, "int")
                ModbusRTU_write_register(1, 0x33, 2, 0, "int")
                ModbusRTU_write_register(1, 0x33, 3, 255, "int")
                delay(50)
                playwav("/wav/nohelment.wav", 1)                
            else
                print("检查到有戴安全帽！")
                Write_sys_register(1002, 1, "int") -- 关闭急停
                SetDO(2, 1)
                delay(50)
                ModbusRTU_write_register(1, 0x33, 5, 2, "int")
                ModbusRTU_write_register(1, 0x33, 1, 0, "int")
                ModbusRTU_write_register(1, 0x33, 2, 255, "int")
                ModbusRTU_write_register(1, 0x33, 3, 0, "int")       
            end 
        else -- 识别其他模式
            Write_sys_register(1002, 1, "int") -- 关闭急停
            SetDO(2, 1)
            delay(50)
            ModbusRTU_write_register(1, 0x33, 5, 0, "int") -- 常亮
            ModbusRTU_write_register(1, 0x33, 1, 0, "int")
            ModbusRTU_write_register(1, 0x33, 2, 255, "int")
            ModbusRTU_write_register(1, 0x33, 3, 0, "int") 
         end
         
            
        
        delay(100)
    end
end

function main()
  release(); --配置为发布版本
  sys_set_com(1, 9600, "none", 8, 1); --485串口，初始化COM1
  HTTP_service(8000, 2);--设置上传数据格式 
  ModbusTCP_service(502,1)--开启modbus TCP服务
  delay(100)
  --添加云变量
  Add_DataPoint("fan", 1001, "int");	--风扇 网关继电器D1
  Add_DataPoint("E_stop", 1002, "int");	--急停开关 网关继电器D2
  
  -- 光照为1 空气质量为2 水浸为3 温湿度为4
  Add_DataPoint("Illuminance",1020,"int");	--光照（只读）
  Add_DataPoint("PM2_5",1021,"int");		--PM2.5（只读）
  Add_DataPoint("PM10",1022,"int");		--PM10（只读）
  Add_DataPoint("PM1",1023,"int");		--PM1.0（只读）
  Add_DataPoint("flooding",1024,"int");	--水浸（只读）
  Add_DataPoint("wendu",1025,"int");	--温度（只读）	
  Add_DataPoint("shidu",1026,"int");	--湿度（只读）
  
  Add_DataPoint("RGB",1030,"int");		--灯光开关 0：关灯 1：开灯
  Add_DataPoint("RGB_mode",1031,"int"); -- 灯带模式 0：常亮 1：呼吸 2：流水灯 3：跑马灯
  Add_DataPoint("Marquee_color",1032,"int"); -- 跑马灯8种颜色（1~8）
  Add_DataPoint("RGB_color",1033,"int"); -- 灯带颜色 1：红 2：绿 3：蓝
  Add_DataPoint("RGB_brightness",1034,"int"); -- 灯光亮度（0~255）
  -- 灯带颜色 三色值
  Add_DataPoint("RGB_color_red",1035,"int"); -- 红色
  Add_DataPoint("RGB_color_green",1036,"int"); -- 绿色
  Add_DataPoint("RGB_color_blue",1037,"int"); -- 蓝色
  
  Add_DataPoint("wd_auto", 1040, "int");	--湿度自动化开关
  Add_DataPoint("sd_auto", 1041, "int");	--湿度自动化开关
  
  Write_sys_register(1001, 0, "int")
  Write_sys_register(1002, 1, "int") 
  Write_sys_register(1037, 255, "int") 
  delay(50)
  
  SetDO(1,0);
  SetDO(2,1); 

  delay(50)
  ModbusRTU_write_register(1, 0x33, 1, 0, "int");
  ModbusRTU_write_register(1, 0x33, 2, 0, "int");
  ModbusRTU_write_register(1, 0x33, 3, 255, "int");
  pthread_create("mode1");
end