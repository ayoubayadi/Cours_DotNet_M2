using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Http;
using TP2_GestionArticles.Models;

namespace TP2_GestionArticles.ViewModels
{
    public class EditViewModel
    {
        public int ProductId { get; set; }

        [Required]
        [StringLength(50, MinimumLength = 5)]
        public string Name { get; set; }

        [Required]
        [Display(Name = "Prix en dinar:")]
        public float Price { get; set; }

        [Required]
        [Display(Name = "Quantité en unité:")]
        public int QteStock { get; set; }

        public int CategoryId { get; set; }
        public Category? Category { get; set; }

        [Display(Name = "Existing Photo:")]
        public string ExistingPhotoPath { get; set; }

        [Display(Name = "Image:")]
        public IFormFile? ImagePath { get; set; }
    }
}