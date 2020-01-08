## PyMacroParser.py要求的几个接口的实现说明
*1.load*
	打开文件，去掉注释、#和define等命令之间的空白字符，将字符串外面的tab换成空格，便于后面解析，保存CPP内容

*2.preDefine*
	存储preDefine指令
    
*3.dumpDict*
- 预定义，保存为一个dict1
- 根据预定义，解析CPP内容（调用用另外一个私有函数递归地求解），保存为另一个dict2，这个dict里面的value是cpp的原内容，所以要么是str类型要么是None
-  返回dict1与dict2的总和dict3
	- 其中dict3根据是返回给dump还是返回给外部的用户，决定是否将dict2中的value解析（调用另外一个私有的函数）成python数据类型，默认是解析的。这样可以保证dump回CPP的内容不丢失精度
    
*4.dump*
调用一次dumpDict，它的第二个默认参数设为false，得到一个合并的dict，写到cpp文件中

*杂项*

未考虑
```
#define  a(short)5
```
这种带有强制类型转换甚至其他函数的东西
	
	

