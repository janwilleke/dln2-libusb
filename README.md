# dln2-libusb
This is a userspace dln2 libusb libary to use https://github.com/notro/pico-usb-io-board without the need of a kernel module.

Also work on android using Termux. Thus this can de a easy way to the usb io ports to an android.

I was to lazy to kompile the kernel module for my host the rpi and the next kernel... and so on. Thus libusb is much more simple.

# first start
python3 dln2.py

should result in one led blink on rpi pico, adn debug output.

# irq example
```
import dln2                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                       
                                                                                                                                                                                                                                                       
def cb(num, val):                                                                                                                                                                                                                                      
    print(f"callback num {num}: {val}")                                                                                                                                                                                                                
                                                                                                                                                                                                                                                       
                                                                                                                                                                                                                                                       
if __name__ == "__main__":                                                                                                                                                                                                                             
    dln = dln2.getdefault()                                                                                                                                                                                                                            
    gp = dln2.Dln2GpioInterface(dln)                                                                                                                                                                                                                   
                                                                                                                                                                                                                                                       
    p = gp.create(6)                                                                                                                                                                                                                                   
    g = gp.create(7)                                                                                                                                                                                                                                   
    p.setirqmask(1,cb)                                                                                                                                                                                                                                 
    g.setirqmask(1,cb)                                                                                                                                                                                                                                 
    dln.irqwait(10000) 

```

# blink example
```
import dln2                                                                                                                                                                                                                                            
import time                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                       
                                                                                                                                                                                                                                                       
dev = dln2.getdefault()                                                                                                                                                                                                                                
gp = dln2.Dln2GpioInterface(dev)                                                                                                                                                                                                                       
led = gp.create(25)                                                                                                                                                                                                                                    
led.setdir(1)                                                                                                                                                                                                                                          
                                                                                                                                                                                                                                                       
while 42:                                                                                                                                                                                                                                              
    led.setval(1)                                                                                                                                                                                                                                      
    if led.getval() != 1:                                                                                                                                                                                                                              
        print("led wrong set")                                                                                                                                                                                                                         
    time.sleep(0.5)                                                                                                                                                                                                                                    
    led.setval(0)                                                                                                                                                                                                                                      
    if led.getval() != 0:                                                                                                                                                                                                                              
        print(f'led get 0: {led.getval()}')                                                                                                                                                                                                            
    time.sleep(0.5)                                                                                                                                                                                                                                    
```
