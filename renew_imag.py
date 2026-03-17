from PIL import Image

img = Image.open("cover.jpg")

img = img.crop((1060,0,4060,3000))  # 裁剪中心
img = img.resize((3000,3000))

img.save("cover_new.jpg", quality=95)