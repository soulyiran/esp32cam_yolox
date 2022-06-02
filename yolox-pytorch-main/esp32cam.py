import numpy as np
import cv2
import socket
import time

import cv2
import numpy as np
from PIL import Image

from yolo import YOLO

if __name__ == '__main__':
    # 创建yolo目标检测模型
    yolo = YOLO()
    # crop 指定了是否在单张图片预测后对目标进行截取
    # count 指定了是否进行目标的计数
    crop = False
    count = False
    fps = 0.0

    usoc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 建一个UDP socket
    usoc.bind(('', 10000))  # 监听端口号
    print("Start!")
    frameIdNow = 0  # 当前帧帧号
    frameSizeNow = 0  # 当前接收到的帧体积
    packetIdNow = 0  # 最新已接收的数据包号
    packetCount = 0  # 当前帧包的数量
    packetLen = 0  # 标准数据包大小
    frameSizeOk = 0  # 当前帧已接收数据量
    jpgBuff = bytes('', 'utf-8')  # 图片数据缓存
    while True:
        # 记录帧开始时间
        t1 = time.time()
        udpbuff, address = usoc.recvfrom(10240)  # 阻塞接收数据，最多一次接收10240字节
        # 解析数据
        frameId = (udpbuff[1] << 24) + (udpbuff[2] << 16) + (udpbuff[3] << 8) + udpbuff[4]  # 获取帧号
        frameSize = (udpbuff[5] << 24) + (udpbuff[6] << 16) + (udpbuff[7] << 8) + udpbuff[8]  # 获取帧体积
        packetId = udpbuff[10]  # 获取包号
        packetSize = (udpbuff[13] << 8) + udpbuff[14]  # 获取包体积

        if frameIdNow != frameId:  # 换帧，记录新一帧的数据信息
            frameIdNow = frameId  # 更新帧号
            frameSizeNow = frameSize  # 更新帧体积
            packetCount = udpbuff[9]  # 更新数据包数量
            packetLen = (udpbuff[11] << 8) + udpbuff[12]  # 更新数据包长度
            frameSizeOk = 0  # 清除当前帧已接收数据量
            packetIdNow = 0  # 最新已接收数据包号清零
            jpgBuff = bytes('', 'utf-8')  # 清空图片数据缓存
        # 复制至缓冲区，并只接收安全范围内的数据包
        if (packetId <= packetCount) and (packetId > packetIdNow):  # 新数据包包号不超过总数据包数量，且包号刚好比前一包多1
            if packetSize == (len(udpbuff) - 15):  # 数据包减去包头等于包体积
                if (packetSize == packetLen) or (packetId == packetCount):  # 标准包或最后一包
                    jpgBuff = jpgBuff + udpbuff[15:]  # 拼接数据包
                    frameSizeOk = frameSizeOk + len(udpbuff) - 15  # 帧数据总量累加
        if frameSizeNow == frameSizeOk:  # 当前帧接收完成
            nparr = np.frombuffer(jpgBuff, dtype=np.uint8)  # 将图片数组转为numpy数组
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # 解码图片

            # 转变成Image
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            # 进行检测
            image = np.array(yolo.detect_image(image))
            # RGBtoBGR满足opencv显示格式
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            # 添加fps数
            fps = (fps + (1. / (time.time() - t1))) / 2
            print("fps= %.2f" % fps)
            image = cv2.putText(image, "fps= %.2f" % fps, (0, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow('ESP', image)  # 将图片显示出来
            if cv2.waitKey(1) == 27:  # 按下ESC键退出
                break
    usoc.close()
