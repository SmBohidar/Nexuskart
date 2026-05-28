from django.contrib import admin
from .models import Product, Variation, ReviewRating, ProductGallery
#import admin_thumbnails
from sorl.thumbnail import get_thumbnail

#@admin_thumbnails.thumbnail('image')
#class ProductGalleryInline(admin.TabularInline):
    #model = ProductGallery
    #extra = 1

class ProductGalleryInline(admin.TabularInline):
    model = ProductGallery
    extra = 1

    # To display the thumbnail in the list
    def thumbnail(self, obj):
        if obj.image:
            thumb = get_thumbnail(obj.image, '100x100', crop='center', quality=99)
            return f'<img src="{thumb.url}" width="{thumb.width}" height="{thumb.height}">'
        return ''
    thumbnail.allow_tags = True
    thumbnail.short_description = 'Thumbnail'

    # Adding 'thumbnail' to the list of fields to be displayed
    readonly_fields = ('thumbnail',)
    fields = ('image', 'thumbnail')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'category', 'modified_date', 'is_available')
    list_editable = ('stock',)
    prepopulated_fields = {'slug': ('product_name',)}
    inlines = [ProductGalleryInline]
    
class VariationAdmin(admin.ModelAdmin):
    list_display = ('product', 'variation_category', 'variation_value', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('product', 'variation_category', 'variation_value')
admin.site.register(Product, ProductAdmin)
admin.site.register(Variation, VariationAdmin)
admin.site.register(ReviewRating)
admin.site.register(ProductGallery)