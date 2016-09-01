# Airvpn toggler

Recentely I've become a user of a great VPN service offered by [Airvpn](https://airvpn.org/).  
I decided, in order to secure and encrypt my connection well, to use it inside an SSL tunnel.  
This I achieved by following the guide shown [here](https://airvpn.org/ssl/).  
I'm not using the airvpn client and I was getting slightly tired with turning on and off
the stunnel and the openvpn connection in seperate terminals whenever I needed to connect or disconnect.  

This small script is the result of that tiredness.  

In order to use this tool, you should accomplish the next steps:  
1. (trivial) Have an Airvpn account.  
2. Be a member of the sudoers group (be able to run ```sudo -s```).  
3. Follow the first part of the Airvpn SSL [guide](https://airvpn.org/ssl/) and download the configuration files.  
   (At the end of this step you should have in some location on your filesystem, one .crt file and a collection of .ssl and .ovpn extensions files) 
   In addition, don't forget to make sure that "stunnel" and "openvpn" are installed on your system.  
4. Place all the downloaded files in a location of your choice. For the next steps I will assume it is in ```/home/your_user_name/airvpn/```   
5. Clone/Download this project and ```cd``` into its folder.  
6. Copy all the files into the airvpn config files folder (i.e ```cp * /home/your_user_name/airvpn/```).  
7. Run ```pip install -r requirements.txt``` to install the needed requirements. Pay attention that installing wx (which is needed in order to show the 
system tray indicator) inside virtualenv is kinda [pain in the ass](http://www.thebrokendesk.com/post/using-wx-python-in-a-virtual-environment/). I would
recommend to avoid it and install it directly on the system.  
  
  
Now you're ready to run it.  

execute ```sudo python airvpn_toggler.py on```, when the script asks you which country you wish to exit from, choose your deisred
country code and that's it.  
You'll know you're good if (1) The script tells you that it has finished successfully. (2) A new system tray icon apeears,
or (3) Issue ```curl -s ipinfo.io/"$(wget http://ipinfo.io/ip -qO -)" | egrep -w "city|region|country"``` and see the results.  

If you wish to turn off the connection, you can either execute "sudo python airvpn_toggler.py off" or right-click the small
system tray icon and choose "Turn Airvpn off".  

In addition, I have a small alias which execute this script in a shorter manner -  
In my aliases file I have the following:  

```bash
alias at='toggleAirvpn'
toggleAirvpn() {  
    cwd=$(pwd)  
    cd /home/your_user_name/airvpn  
    sudo /home/your_user_name/airvpn/airvpn_toggler.py $1  
    cd $cwd  
}
```  
  
(don't forget to source it after the change, i.e ```. ~/.bashrc```)  

and I run by it issuing ```at on``` or ```at off```
  
Cheers.
