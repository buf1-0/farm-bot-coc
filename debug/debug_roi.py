import cv2, numpy as np, pyautogui
from configuration import Configuration

cfg = Configuration()
img = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
h, w = img.shape[:2]

x0, y0, x1, y1 = cfg.GAME_ROI
cv2.rectangle(img,
              (int(x0*w), int(y0*h)),
              (int(x1*w), int(y1*h)),
              (0, 255, 0), 3)

cv2.imshow("ROI Preview", img)
cv2.waitKey(0)