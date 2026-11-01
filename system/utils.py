#memory conversion constants
kb=1024
mb=kb*kb
gb=mb*kb

#####
#convert function
#####
def bytesformat(bytes_num):
    if bytes_num >= gb:
        return f"{bytes_num/gb:.2f} GB"
    elif bytes_num >= mb:
        return f"{bytes_num/mb:.2f} MB"
    elif bytes_num >= kb:
        return f"{bytes_num/kb:.2f} KB"
    else:
        return f"{bytes_num} Bytes"

#####
#the mb/s function for network speed
#####
def speedformat(bytessecond):
    if bytessecond >= gb:
        return f"{bytessecond/gb:.2f} GB/s"
    elif bytessecond >= mb:
        return f"{bytessecond/mb:.2f} MB/s"
    elif bytessecond >= kb:
        return f"{bytessecond/kb:.2f} KB/s"
    else:
        return f"{bytessecond} Bytes/s"
    