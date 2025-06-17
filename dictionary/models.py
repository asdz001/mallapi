from django.db import models



#브랜드매핑
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="표준 브랜드명")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "브랜드매핑"
        verbose_name_plural = "A. 브랜드매핑"


class BrandAlias(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="aliases", verbose_name="표준 브랜드")
    alias = models.CharField(max_length=100, unique=True, verbose_name="치환 브랜드명")

    def __str__(self):
        return f"{self.alias} → {self.brand.name}"




class ForbiddenWord(models.Model):
    word = models.CharField(max_length=100, unique=True, verbose_name="금칙어")

    def __str__(self):
        return self.word




#카테고리
# ✅ 성별
class CategoryLevel1(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="표준 성별")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "성별"
        verbose_name_plural = "1. 성별"


class CategoryLevel1Alias(models.Model):
    alias = models.CharField(max_length=100, unique=True, verbose_name="치환 성별")
    category = models.ForeignKey(CategoryLevel1, on_delete=models.CASCADE, related_name="aliases")

    def __str__(self):
        return f"{self.alias} → {self.category.name}"


# ✅ 대분류
class CategoryLevel2(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="표준 대분류")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "대분류"
        verbose_name_plural = "2. 대분류"


class CategoryLevel2Alias(models.Model):
    alias = models.CharField(max_length=100, unique=True, verbose_name="치환 대분류")
    category = models.ForeignKey(CategoryLevel2, on_delete=models.CASCADE, related_name="aliases")

    def __str__(self):
        return f"{self.alias} → {self.category.name}"




# ✅ 중분류
class CategoryLevel3(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="표준 중분류")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "중분류"
        verbose_name_plural = "3. 중분류"


class CategoryLevel3Alias(models.Model):
    alias = models.CharField(max_length=100, unique=True, verbose_name="치환 중분류")
    category = models.ForeignKey(CategoryLevel3, on_delete=models.CASCADE, related_name="aliases")

    def __str__(self):
        return f"{self.alias} → {self.category.name}"





# ✅ 소분류
class CategoryLevel4(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="표준 소분류")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "소분류"
        verbose_name_plural = "4. 소분류"    

class CategoryLevel4Alias(models.Model):
    alias = models.CharField(max_length=100, unique=True, verbose_name="치환 소분류")
    category = models.ForeignKey(CategoryLevel4, on_delete=models.CASCADE, related_name="aliases")

    def __str__(self):
        return f"{self.alias} → {self.category.name}"
    
