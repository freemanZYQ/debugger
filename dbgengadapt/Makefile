all: dbgengadapt.dll

dbgengadapt.dll: dbgengadapt.obj
	link dbgengadapt.obj dbgeng.lib /DLL /OUT:dbgengadapt.dll

dbgengadapt.obj: dbgengadapt.cpp
	cl dbgengadapt.cpp /c /O1 /EHsc /Fo:dbgengadapt.obj

clean:
	rm *.dll *.obj
