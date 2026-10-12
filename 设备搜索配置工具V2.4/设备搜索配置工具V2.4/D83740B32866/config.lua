--设置网口信息

--在该处设置网络参数ip、掩码、网关
--sys_set_eth0("192.168.1.233", "255.255.255.0", "192.168.1.1"); 

sys_set_com(1, 9600, "none", 8, 1); 
Add_DataPoint("Device_id", 1101, "long");
Add_DataPoint("val1", 1001, "float");
Add_DataPoint("val2", 1003, "float");
Add_DataPoint("val3", 1005, "float");
Add_DataPoint("val4", 1007, "float");
Add_DataPoint("val5", 1009, "float");
Add_DataPoint("ctrl", 1016, "int");
Write_DataPoint("Device_id", 12345678);--在该处设置设备ID，如12345678
HTTP_service(8000, 2);--设置上传数据格式
lora_debug_mode(3353, 9600, "NONE", 8, 1)
while 1 do 
--读取铵离子（设备地址2，寄存器1）
    local NH4, ret = ModbusRTU_read_hold_register(1, 2, 1, 1,"float1234")
        if ret == 1 then
          print(string.format("NH4:%.1f\n", NH4))
          Write_DataPoint("val1", NH4)
        end
		
--读取油性（设备地址1，寄存器1）
    local oil_value, ret = ModbusRTU_read_hold_register(1, 1, 1, 1, "float1234")
        if ret == 1 then
          print(string.format("oil:%.1f\n", oil_value))
          Write_DataPoint("oil", oil_value)
        end
        
--读取光学浊度（设备地址3，寄存器1）
    local light_value, ret = ModbusRTU_read_hold_register(1, 3, 1, 1, "float1234")
        if ret == 1 then
          print(string.format("light:%.1f\n", light_value))
          Write_DataPoint("light", light_value)
        end
--读取雷达液位计（高位，液位）（寄存器1-3）
    local val1,val2,val3, ret = ModbusRTU_read_hold_register(1, 4, 1, 3, "int")
        if ret == 1 then
          val1=val1/1000
          val3=val3/1000
          print(string.format("waterH:%.3f，high:%.3f\n", val1,val3))
          Write_DataPoint("waterH", val1)
	      Write_DataPoint("high", val3)
        end
--打印值
	   --print(string.format("通道一%f\n", val1))
	   --print(string.format("通道二%f\n", val2))
	   --print(string.format("通道三%f\n", val3))
	   --print(string.format("通道四%f\n", val4))
	   
	   --在该处指定服务器IP，如192.168.1.5 
    POST_request("http://192.168.1.5:8450/mj/gapi/getdata/");
    delay(1000);
end