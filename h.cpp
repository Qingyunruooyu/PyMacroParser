//#define x1
//#define x2
#ifdef x1								//	x1
#ifdef x2							//	x1,x2
#ifndef x2						//	x1,x2		x2
#ifndef x2	
#endif

//#endif
//ffff # endif

#ifdef x
#endif	
//	//
#else //这个else	sd					//	//

#endif  	//这个endif不管用			//	//

#else
#define ttt 333				//	
#endif							//	
#else	//??						
#ifndef x2						
#define ttt 444				
#else							
#define ttt 555				
#endif							/
#endif								//	
